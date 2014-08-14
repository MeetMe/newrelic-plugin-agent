"""
Multiple Plugin Agent for the New Relic Platform

"""
import helper
import importlib
import json
import logging
import os
import requests
import socket
import sys
import Queue as queue
import threading
import time

from newrelic_plugin_agent import __version__
from newrelic_plugin_agent import plugins

LOGGER = logging.getLogger(__name__)


class NewRelicPluginAgent(helper.Controller):
    """The NewRelicPluginAgent class implements a agent that polls plugins
    every minute and reports the state to NewRelic.

    """
    IGNORE_KEYS = ['license_key', 'proxy', 'endpoint',
                   'poll_interval', 'wake_interval']
    MAX_METRICS_PER_REQUEST = 10000
    PLATFORM_URL = 'https://platform-api.newrelic.com/platform/v1/metrics'
    WAKE_INTERVAL = 60

    def __init__(self, args, operating_system):
        """Initialize the NewRelicPluginAgent object.

        :param argparse.Namespace args: Command line arguments
        :param str operating_system: The operating_system name

        """
        super(NewRelicPluginAgent, self).__init__(args, operating_system)
        self.derive_last_interval = dict()
        self.endpoint = self.PLATFORM_URL
        self.http_headers = {'Accept': 'application/json',
                             'Content-Type': 'application/json'}
        self.last_interval_start = None
        self.min_max_values = dict()
        self._wake_interval = (self.config.application.get('wake_interval') or
                               self.config.application.get('poll_interval') or
                               self.WAKE_INTERVAL)
        self.next_wake_interval = int(self._wake_interval)
        self.publish_queue = queue.Queue()
        self.threads = list()
        info = tuple([__version__] + list(self.system_platform))
        LOGGER.info('Agent v%s initialized, %s %s v%s', *info)

    def setup(self):
        """Setup the internal state for the controller class. This is invoked
        on Controller.run().

        Items requiring the configuration object should be assigned here due to
        startup order of operations.

        """
        if hasattr(self.config.application, 'endpoint'):
            self.endpoint = self.config.application.endpoint
        self.http_headers['X-License-Key'] = self.license_key
        self.last_interval_start = time.time()

    @property
    def agent_data(self):
        """Return the agent data section of the NewRelic Platform data payload

        :rtype: dict

        """
        return {'host': socket.gethostname(),
                'pid': os.getpid(),
                'version': __version__}

    @property
    def license_key(self):
        """Return the NewRelic license key from the configuration values.

        :rtype: str

        """
        return self.config.application.license_key

    def poll_plugin(self, plugin_name, plugin, config):
        """Kick off a background thread to run the processing task.

        :param newrelic_plugin_agent.plugins.base.Plugin plugin: The plugin
        :param dict config: The config for the plugin

        """

        if not isinstance(config, (list, tuple)):
            config = [config]

        for instance in config:
            thread = threading.Thread(target=self.thread_process,
                                      kwargs={'config': instance,
                                              'name': plugin_name,
                                              'plugin': plugin,
                                              'poll_interval':
                                                  int(self._wake_interval)})
            thread.run()
            self.threads.append(thread)

    def process(self):
        """This method is called after every sleep interval. If the intention
        is to use an IOLoop instead of sleep interval based daemon, override
        the run method.

        """
        start_time = time.time()
        self.start_plugin_polling()

        # Sleep for a second while threads are running
        while self.threads_running:
            time.sleep(1)

        self.threads = list()
        self.send_data_to_newrelic()
        duration = time.time() - start_time
        self.next_wake_interval = self._wake_interval - duration
        if self.next_wake_interval < 1:
            LOGGER.warning('Poll interval took greater than %i seconds',
                           duration)
            self.next_wake_interval = int(self._wake_interval)
        LOGGER.info('Stats processed in %.2f seconds, next wake in %i seconds',
                    duration, self.next_wake_interval)

    def process_min_max_values(self, component):
        """Agent keeps track of previous values, so compute the differences for
        min/max values.

        :param dict component: The component to calc min/max values for

        """
        guid = component['guid']
        name = component['name']

        if guid not in self.min_max_values.keys():
            self.min_max_values[guid] = dict()

        if name not in self.min_max_values[guid].keys():
            self.min_max_values[guid][name] = dict()

        for metric in component['metrics']:
            min_val, max_val = self.min_max_values[guid][name].get(metric,
                                                                   (None, None))
            value = component['metrics'][metric]['total']
            if min_val is not None and min_val > value:
                min_val = value

            if max_val is None or max_val < value:
                max_val = value

            if component['metrics'][metric]['min'] is None:
                component['metrics'][metric]['min'] = min_val or value

            if component['metrics'][metric]['max'] is None:
                component['metrics'][metric]['max'] = max_val

            self.min_max_values[guid][name][metric] = min_val, max_val

    @property
    def proxies(self):
        """Return the proxy used to access NewRelic.

        :rtype: dict

        """
        if 'proxy' in self.config.application:
            return {
                'http': self.config.application['proxy'],
                'https': self.config.application['proxy']
            }
        return None

    def send_data_to_newrelic(self):
        metrics = 0
        components = list()
        while self.publish_queue.qsize():
            (name, data, last_values) = self.publish_queue.get()
            self.derive_last_interval[name] = last_values
            if isinstance(data, list):
                for component in data:
                    self.process_min_max_values(component)
                    components.append(component)
                    metrics += len(component['metrics'].keys())
                    if metrics >= self.MAX_METRICS_PER_REQUEST:
                        self.send_components(components, metrics)
                        components = list()
                        metrics = 0

            elif isinstance(data, dict):
                self.process_min_max_values(data)
                components.append(data)
                metrics += len(data['metrics'].keys())
                if metrics >= self.MAX_METRICS_PER_REQUEST:
                    self.send_components(components, metrics)
                    components = list()
                    metrics = 0

        LOGGER.debug('Done, will send remainder of %i metrics', metrics)
        self.send_components(components, metrics)

    def send_components(self, components, metrics):
        """Create the headers and payload to send to NewRelic platform as a
        JSON encoded POST body.

        """
        if not metrics:
            LOGGER.warning('No metrics to send to NewRelic this interval')
            return

        LOGGER.info('Sending %i metrics to NewRelic', metrics)
        body = {'agent': self.agent_data, 'components': components}
        LOGGER.debug(body)
        try:
            response = requests.post(self.endpoint,
                                     headers=self.http_headers,
                                     proxies=self.proxies,
                                     data=json.dumps(body, ensure_ascii=False),
                                     timeout=self.config.get('newrelic_api_timeout', 10),
                                     verify=self.config.get('verify_ssl_cert',
                                                            True))
            LOGGER.debug('Response: %s: %r',
                         response.status_code,
                         response.content.strip())
        except requests.ConnectionError as error:
            LOGGER.error('Error reporting stats: %s', error)
        except requests.Timeout as error:
            LOGGER.error('TimeoutError reporting stats: %s', error)

    @staticmethod
    def _get_plugin(plugin_path):
        """Given a qualified class name (eg. foo.bar.Foo), return the class

        :rtype: object

        """
        try:
            package, class_name = plugin_path.rsplit('.', 1)
        except ValueError:
            return None

        try:
            module_handle = importlib.import_module(package)
            class_handle = getattr(module_handle, class_name)
            return class_handle
        except ImportError:
            LOGGER.exception('Attempting to import %s', plugin_path)
            return None

    def start_plugin_polling(self):
        """Iterate through each plugin and start the polling process."""
        for plugin in [key for key in self.config.application.keys()
                       if key not in self.IGNORE_KEYS]:
            LOGGER.info('Enabling plugin: %s', plugin)
            plugin_class = None

            # If plugin is part of the core agent plugin list
            if plugin in plugins.available:
                plugin_class = self._get_plugin(plugins.available[plugin])

            # If plugin is in config and a qualified class name
            elif '.' in plugin:
                plugin_class = self._get_plugin(plugin)

            # If plugin class could not be imported
            if not plugin_class:
                LOGGER.error('Enabled plugin %s not available', plugin)
                continue

            self.poll_plugin(plugin, plugin_class,
                             self.config.application.get(plugin))

    @property
    def threads_running(self):
        """Return True if any of the child threads are alive

        :rtype: bool

        """
        for thread in self.threads:
            if thread.is_alive():
                return True
        return False

    def thread_process(self, name, plugin, config, poll_interval):
        """Created a thread process for the given name, plugin class,
        config and poll interval. Process is added to a Queue object which
        used to maintain the stack of running plugins.

        :param str name: The name of the plugin
        :param newrelic_plugin_agent.plugin.Plugin plugin: The plugin class
        :param dict config: The plugin configuration
        :param int poll_interval: How often the plugin is invoked

        """
        instance_name = "%s:%s" % (name, config.get('name', 'unnamed'))
        obj = plugin(config, poll_interval,
                     self.derive_last_interval.get(instance_name))
        obj.poll()
        self.publish_queue.put((instance_name, obj.values(),
                                obj.derive_last_interval))

    @property
    def wake_interval(self):
        """Return the wake interval in seconds as the number of seconds
        until the next minute.

        :rtype: int

        """
        return self.next_wake_interval


def main():
    helper.parser.description('The NewRelic Plugin Agent polls various '
                              'services and sends the data to the NewRelic '
                              'Platform')
    helper.parser.name('newrelic_plugin_agent')
    argparse = helper.parser.get()
    argparse.add_argument('-C',
                          action='store_true',
                          dest='configure',
                          help='Run interactive configuration')
    args = helper.parser.parse()
    if args.configure:
        print('Configuration')
        sys.exit(0)
    helper.start(NewRelicPluginAgent)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    main()
