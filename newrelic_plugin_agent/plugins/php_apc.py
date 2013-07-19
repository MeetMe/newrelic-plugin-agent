"""
PHP APC Support

"""
import logging
import requests
import time

from newrelic_plugin_agent.plugins import base

LOGGER = logging.getLogger(__name__)

class APC(base.Plugin):

    GUID = 'com.meetme.newrelic_php_apc_agent'

    def add_datapoints(self, stats):
        """Add all of the data points for a node

        :param str stats: The stats content from APC as a string

        """
        shared_memory = stats.get('shared_memory', dict())
        self.add_gauge_value('Shared Memory/Available', 'Bytes',
                             shared_memory.get('avail_mem', 0))
        self.add_gauge_value('Shared Memory/Segment Size', 'Bytes',
                             shared_memory.get('seg_size', 0))
        self.add_gauge_value('Shared Memory/Segment Count', '',
                             shared_memory.get('num_seg', 0))

        user_stats = stats.get('user_stats', dict())
        self.add_gauge_value('User Cache/Slots', '',
                             user_stats.get('num_slots', 0))
        self.add_gauge_value('User Cache/Entries', '',
                             user_stats.get('num_entries', 0))
        self.add_gauge_value('User Cache/Size', 'Bytes',
                             user_stats.get('mem_size', 0))
        self.add_gauge_value('User Cache/Expunges', '',
                             user_stats.get('expunges', 0))

        hits = user_stats.get('num_hits', 0)
        misses = user_stats.get('num_misses', 0)
        total = hits + misses
        if total > 0:
            effectiveness = float(float(hits) / float(total)) * 100
        else:
            effectiveness = 0
        self.add_gauge_value('User Cache/Effectiveness', '%', effectiveness)

        self.add_derive_value('User Cache/Hits', '', hits)
        self.add_derive_value('User Cache/Misses', '', misses)
        self.add_derive_value('User Cache/Inserts', '',
                              user_stats.get('num_inserts', 0))

    @property
    def apc_stats_url(self):
        if 'scheme' not in self.config:
            self.config['scheme'] = 'http'
        return '%(scheme)s://%(host)s:%(port)s%(path)s?auto' % self.config

    def fetch_data(self):
        """Fetch the data from the APC script

        :rtype: str

        """
        kwargs = {'url': self.apc_stats_url,
                  'verify': self.config.get('verify_ssl_cert', True)}
        if 'username' in self.config and 'password' in self.config:
            kwargs['auth'] = (self.config['username'], self.config['password'])

        try:
            response = requests.get(**kwargs)
        except requests.ConnectionError as error:
            LOGGER.error('Error polling APC Stats: %s', error)
            return {}

        if response.status_code == 200:
            try:
                return response.json()
            except Exception as error:
                LOGGER.error('JSON decoding error: %r', error)
                return ''
        LOGGER.error('Error response from %s (%s): %s', self.apc_stats_url,
                     response.status_code, response.content)
        return ''

    def poll(self):
        LOGGER.info('Polling APC Stats via %s', self.apc_stats_url)
        start_time = time.time()
        if 'scheme' not in self.config:
            self.config['scheme'] = 'http'
        self.derive = dict()
        self.gauge = dict()
        self.rate = dict()
        data = self.fetch_data()
        if data:
            self.add_datapoints(data)
            LOGGER.info('Polling complete in %.2f seconds',
                        time.time() - start_time)
        else:
            LOGGER.error('No data was returned from APC. Ensure '
                         'configuration is correct and that %s is reachable '
                         'by the agent', self.apc_stats_url)
