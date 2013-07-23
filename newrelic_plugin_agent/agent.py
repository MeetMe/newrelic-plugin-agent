"""
Multiple Plugin Agent for the New Relic Platform

"""
import clihelper
import importlib
import json
import logging
import os
from yaml import parser
import platform
import requests
import socket
import Queue as queue
import threading
import time

from newrelic_plugin_agent import __version__
from newrelic_plugin_agent import plugins

LOGGER = logging.getLogger(__name__)


class NewRelicPluginAgent(clihelper.Controller):
    """The NewRelicPluginAgent class implements a agent that polls plugins
    every minute and reports the state to NewRelic.

    """
    IGNORE_KEYS = ['license_key', 'poll_interval', 'proxy', 'endpoint']
    MAX_METRICS_PER_REQUEST = 10000
    PLATFORM_URL = 'https://platform-api.newrelic.com/platform/v1/metrics'

    def __init__(self, options, arguments):
        """Create an instance of the controller passing in the debug flag,
        the options and arguments from the cli parser.

        :param optparse.Values options: OptionParser option values
        :param list arguments: Left over positional cli arguments

        """
        self.next_wake_interval = self.WAKE_INTERVAL
        super(NewRelicPluginAgent, self).__init__(options, arguments)
        self.publish_queue = queue.Queue()
        self.threads = list()
        self._wake_interval = self.application_config.get('poll_interval',
                                                          self.WAKE_INTERVAL)
        self.endpoint = self.application_config.get('endpoint',
                                                    self.PLATFORM_URL)
        self.http_headers = {'Accept': 'application/json',
                             'Content-Type': 'application/json',
                             'X-License-Key': self.license_key}
        self.derive_last_interval = dict()
        self.min_max_values = dict()
        distro = ' '.join(platform.linux_distribution()).strip()
        os = platform.platform(True, True)
        if distro:
            os += ' (%s)' % distro
        LOGGER.debug('Agent v%s initialized, %s %s on %s',
                     __version__,
                     platform.python_implementation(),
                     platform.python_version(), os)

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
        return self.application_config['license_key']

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
                                              'poll_interval': self._wake_interval})
            thread.run()
            self.threads.append(thread)

    def process(self):
        """This method is called after every sleep interval. If the intention
        is to use an IOLoop instead of sleep interval based daemon, override
        the run method.

        """
        start_time = time.time()
        self.start_plugin_polling()
        while self.threads_running:
            self._sleep()
        self.threads = list()
        self.send_data_to_newrelic()
        duration = time.time() - start_time
        self.next_wake_interval = self._wake_interval - duration
        if self.next_wake_interval < 0:
            LOGGER.warning('Poll interval took greater than %i seconds',
                           self._wake_interval)
            self.next_wake_interval = self._wake_interval
        LOGGER.info('All stats processed in %.2f seconds, next wake in %.2f',
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
        if 'proxy' in self.application_config:
            return {
                'http': self.application_config['proxy'],
                'https': self.application_config['proxy']
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
                    metrics += len(component['metrics'].keys())
                    if metrics >= self.MAX_METRICS_PER_REQUEST:
                        self.send_components(components, metrics)
                        components = list()
                        metrics = 0
                    components.append(component)

            elif isinstance(data, dict):
                self.process_min_max_values(data)
                metrics += len(data['metrics'].keys())
                if metrics >= self.MAX_METRICS_PER_REQUEST:
                    self.send_components(components, metrics)
                    components = list()
                    metrics = 0
                components.append(data)

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
                                     verify=self.config.get('verify_ssl_cert',
                                                            True))
            LOGGER.debug('Response: %s: %r',
                         response.status_code,
                         response.content.strip())
        except requests.ConnectionError as error:
            LOGGER.error('Error reporting stats: %s', error)

    def setup(self):
        self.last_interval_start = time.time()

    def start_plugin_polling(self):
        enabled_plugins = [key for key in self.application_config.keys()
                           if key not in self.IGNORE_KEYS]
        for plugin in enabled_plugins:
            if plugin in plugins.available:
                plugin_parts = plugins.available[plugin].split('.')
                package = '.'.join(plugin_parts[:-1])
                LOGGER.debug('Attempting to import %s', package)
                module_handle = importlib.import_module(package)
                class_handle = getattr(module_handle, plugin_parts[-1])
                self.poll_plugin(plugin, class_handle,
                                 self.application_config.get(plugin))
            else:
                LOGGER.error('Enabled plugin %s not available', plugin)

    @property
    def threads_running(self):
        for thread in self.threads:
            if thread.is_alive():
                return True
        return False

    def thread_process(self, name, plugin, config, poll_interval):
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
    clihelper.setup('newrelic_plugin_agent',
                    'New Relic Platform Plugin Agent',
                    __version__)
    try:
        clihelper.run(NewRelicPluginAgent)
    except parser.ParserError as error:
        logging.basicConfig(level=logging.CRITICAL)
        LOGGER.critical('Parsing of configuration file failed: %s', error)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    main()
