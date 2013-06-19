"""
Multiple Plugin Agent for the New Relic Platform

"""
import clihelper
import json
import logging
import os
import requests
import socket
import Queue as queue
import threading
import time

from newrelic_plugin_agent import __version__

LOGGER = logging.getLogger(__name__)


class NewRelicPluginAgent(clihelper.Controller):
    """The NewRelicPluginAgent class implements a agent that polls plugins
    every minute and reports the state to NewRelic.

    """
    IGNORE_KEYS = ['license_key', 'poll_interval']
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
        self.http_headers = {'Accept': 'application/json',
                             'Content-Type': 'application/json',
                             'X-License-Key': self.license_key}
        self.derive_last_interval = dict()
        self.min_max_values = dict()

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

        thread = threading.Thread(target=self.thread_process,
                                  kwargs={'config': config,
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
        LOGGER.info('Polling')
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
        LOGGER.info('Sending %i metrics to NewRelic', metrics)
        body = {'agent': self.agent_data, 'components': components}
        LOGGER.debug(body)
        try:
            response = requests.post(self.PLATFORM_URL,
                                     headers=self.http_headers,
                                     data=json.dumps(body, ensure_ascii=False))
            LOGGER.debug('Response: %s: %r',
                         response.status_code,
                         response.content.strip())
        except requests.ConnectionError as error:
            LOGGER.error('Error reporting stats: %s', error)

    def setup(self):
        self.last_interval_start = time.time()

    def start_plugin_polling(self):

        plugins = [key for key in self.application_config.keys()
                   if key not in self.IGNORE_KEYS]

        for plugin in plugins:

            if plugin == 'apache_httpd':
                if 'apache_httpd' not in globals():
                    from newrelic_plugin_agent.plugins import apache_httpd
                self.poll_plugin(plugin, apache_httpd.ApacheHTTPD,
                                 self.application_config.get(plugin))

            if plugin == 'couchdb':
                if 'couchdb' not in globals():
                    from newrelic_plugin_agent.plugins import couchdb
                self.poll_plugin(plugin, couchdb.CouchDB,
                                 self.application_config.get(plugin))

            elif plugin == 'edgecast':
                if 'edgecast' not in globals():
                    from newrelic_plugin_agent.plugins import edgecast
                self.poll_plugin(plugin, edgecast.Edgecast,
                                 self.application_config.get(plugin))

            elif plugin == 'memcached':
                if 'memcached' not in globals():
                    from newrelic_plugin_agent.plugins import memcached
                self.poll_plugin(plugin, memcached.Memcached,
                                 self.application_config.get(plugin))

            elif plugin == 'mongodb':
                if 'mongodb' not in globals():
                    from newrelic_plugin_agent.plugins import mongodb
                self.poll_plugin(plugin, mongodb.MongoDB,
                                 self.application_config.get(plugin))

            elif plugin == 'nginx':
                if 'nginx' not in globals():
                    from newrelic_plugin_agent.plugins import nginx
                self.poll_plugin(plugin, nginx.Nginx,
                                 self.application_config.get(plugin))

            elif plugin == 'pgbouncer':
                if 'pgbouncer' not in globals():
                    from newrelic_plugin_agent.plugins import pgbouncer
                self.poll_plugin(plugin, pgbouncer.PgBouncer,
                                 self.application_config.get(plugin))

            elif plugin == 'postgresql':
                if 'postgresql' not in globals():
                    from newrelic_plugin_agent.plugins import postgresql
                self.poll_plugin(plugin, postgresql.PostgreSQL,
                                 self.application_config.get(plugin))

            elif plugin == 'rabbitmq':
                if 'rabbitmq' not in globals():
                    from newrelic_plugin_agent.plugins import rabbitmq
                self.poll_plugin(plugin, rabbitmq.RabbitMQ,
                                 self.application_config.get(plugin))

            elif plugin == 'redis':
                if 'redis' not in globals():
                    from newrelic_plugin_agent.plugins import redis
                self.poll_plugin(plugin, redis.Redis,
                                 self.application_config.get(plugin))

            elif plugin == 'riak':
                if 'riak' not in globals():
                    from newrelic_plugin_agent.plugins import riak
                self.poll_plugin(plugin, riak.Riak,
                                 self.application_config.get(plugin))

    @property
    def threads_running(self):
        for thread in self.threads:
            if thread.is_alive():
                return True
        return False

    def thread_process(self, name, plugin, config, poll_interval):
        LOGGER.debug('Polling %s, %r, %r, %r',
                     name, plugin, config, poll_interval)
        obj = plugin(config, poll_interval, self.derive_last_interval.get(name))
        obj.poll()
        self.publish_queue.put((name, obj.values(), obj.derive_last_interval))

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
    clihelper.run(NewRelicPluginAgent)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    main()
