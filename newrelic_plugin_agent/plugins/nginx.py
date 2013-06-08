"""
Nginx Support

"""
import logging
import re
import requests
import time

from newrelic_plugin_agent.plugins import base

LOGGER = logging.getLogger(__name__)

PATTERN = re.compile(r'^Active connections\:\s(?P<connections>\d+)\s+\n'
                     r'server accepts handled requests\n\s+(?P<accepts>\d+)'
                     r'\s+(?P<handled>\d+)\s+(?P<requests>\d+)\s+\nReading\:'
                     r'\s+(?P<reading>\d+)\s+Writing\:\s+(?P<writing>\d+)'
                     r'\s+Waiting\:\s+(?P<waiting>\d+)')


class Nginx(base.Plugin):

    GUID = 'com.meetme.newrelic_nginx_agent'

    GAUGES = ['connections', 'reading', 'writing', 'waiting']
    KEYS = {'connections': 'Totals/Connections',
            'accepts': 'Requests/Accepted',
            'handled': 'Requests/Handled',
            'requests': 'Totals/Requests',
            'reading': 'Connections/Reading',
            'writing': 'Connections/Writing',
            'waiting': 'Connections/Waiting'}

    TYPES = {'connections': '',
            'accepts': '',
            'handled': '',
            'requests': '',
            'reading': '',
            'writing': '',
            'waiting': ''}

    def add_datapoints(self, stats):
        """Add all of the data points for a node

        :param str stats: The stub stats content

        """
        matches = PATTERN.match(stats)
        if matches:
            for key in self.KEYS.keys():
                try:
                    value = int(matches.group(key))
                except (IndexError, ValueError):
                    value = 0
                if key in self.GAUGES:
                    self.add_gauge_value(self.KEYS[key], '', value)
                else:
                    self.add_derive_value(self.KEYS[key], '', value)

    @property
    def nginx_stats_url(self):
        return 'http://%(host)s:%(port)s/%(path)s' % self.config

    def fetch_data(self):
        """Fetch the data from the Nginx server for the specified data type

        :rtype: str

        """
        try:
            response = requests.get(self.nginx_stats_url)
        except requests.ConnectionError as error:
            LOGGER.error('Error polling Nginx: %s', error)
            return {}

        if response.status_code == 200:
            try:
                return response.content
            except Exception as error:
                LOGGER.error('JSON decoding error: %r', error)
                return ''
        LOGGER.error('Error response from %s (%s): %s', self.nginx_stats_url,
                     response.status_code, response.content)
        return ''

    def poll(self):
        LOGGER.info('Polling Nginx at %s', self.nginx_stats_url)
        start_time = time.time()
        self.derive = dict()
        self.gauge = dict()
        self.rate = dict()
        self.add_datapoints(self.fetch_data())
        LOGGER.info('Polling complete in %.2f seconds',
                    time.time() - start_time)
