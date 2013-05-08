"""
Redis Agent for the New Relic Platform

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

__version__ = '0.1.0'

LOGGER = logging.getLogger(__name__)


class NewRelicPluginAgent(clihelper.Controller):
    """The NewRelicRedisAgent class implements a agent that polls Redis
    every minute and reports the state of a Redis cluster to NewRelic.

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

    def poll_plugin(self, plugin, config):
        """Kick off a background thread to run the processing task.

        :param newrelic_plugin_agent.plugins.base.Plugin plugin: The plugin
        :param dict config: The config for the plugin

        """

        thread = threading.Thread(target=self.thread_process,
                                  kwargs={'config': config,
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
        LOGGER.info('All stats processed in %.2f seconds, next wake in %.2f',
                    duration, self.next_wake_interval)

    def send_data_to_newrelic(self):
        metrics = 0
        components = list()
        while self.publish_queue.qsize():
            data = self.publish_queue.get()
            if isinstance(data, list):
                for component in data:
                    metrics += len(component['metrics'].keys())
                    if metrics >= self.MAX_METRICS_PER_REQUEST:
                        self.send_components(components, metrics)
                        components = list()
                        metrics = 0
                    components.append(component)
            elif isinstance(data, dict):
                metrics += len(data['metrics'].keys())
                if metrics >= self.MAX_METRICS_PER_REQUEST:
                    self.send_components(components, metrics)
                    components = list()
                    metrics = 0
                components.append(data)
        self.send_components(components, metrics)

    def send_components(self, components, metrics):
        """Create the headers and payload to send to NewRelic platform as a
        JSON encoded POST body.

        """

        LOGGER.info('Sending %i metrics to NewRelic', metrics)
        body = {'agent': self.agent_data, 'components': components}
        try:
            response = requests.post(self.PLATFORM_URL,
                                     headers=self.http_headers,
                                     data=json.dumps(body, ensure_ascii=False))
            LOGGER.info('Response: %s: %r',
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

            if plugin == 'couchdb':
                if 'couchdb' not in globals():
                    from newrelic_plugin_agent.plugins import couchdb
                self.poll_plugin(couchdb.CouchDB,
                                 self.application_config.get(plugin))

            elif plugin == 'memcached':
                if 'memcached' not in globals():
                    from newrelic_plugin_agent.plugins import memcached
                self.poll_plugin(memcached.Memcached,
                                 self.application_config.get(plugin))

            elif plugin == 'rabbitmq':
                if 'rabbitmq' not in globals():
                    from newrelic_plugin_agent.plugins import rabbitmq
                self.poll_plugin(rabbitmq.RabbitMQ,
                                 self.application_config.get(plugin))

            elif plugin == 'redis':
                if 'redis' not in globals():
                    from newrelic_plugin_agent.plugins import redis
                self.poll_plugin(redis.Redis,
                                 self.application_config.get(plugin))

    @property
    def threads_running(self):
        for thread in self.threads:
            if thread.is_alive():
                return True
        return False

    def thread_process(self, plugin, config, poll_interval):
        obj = plugin(config, poll_interval)
        obj.poll()
        values = obj.values()
        self.publish_queue.put(values)

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
