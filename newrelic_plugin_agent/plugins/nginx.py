"""
Nginx Support

"""
import logging
import re

from newrelic_plugin_agent.plugins import base

LOGGER = logging.getLogger(__name__)

PATTERN = re.compile(r'^Active connections\:\s(?P<connections>\d+)\s+\n'
                     r'server accepts handled requests\n\s+(?P<accepts>\d+)'
                     r'\s+(?P<handled>\d+)\s+(?P<requests>\d+)\s+\nReading\:'
                     r'\s+(?P<reading>\d+)\s+Writing\:\s+(?P<writing>\d+)'
                     r'\s+Waiting\:\s+(?P<waiting>\d+)')


class Nginx(base.HTTPStatsPlugin):

    DEFAULT_PATH = 'nginx_stub_status'
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
        if not stats:
            return
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
