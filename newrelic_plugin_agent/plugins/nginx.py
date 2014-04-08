"""
Nginx Support

"""
import logging
import re

from newrelic_plugin_agent.plugins import base

LOGGER = logging.getLogger(__name__)

PATTERN = re.compile(r'^Active connections: (?P<connections>\d+)\s+[\w ]+\n'
                     r'\s+(?P<accepts>\d+)'
                     r'\s+(?P<handled>\d+)'
                     r'\s+(?P<requests>\d+)'
                     r'(\s+(?P<time>\d+)|)'
                     r'\s+Reading:\s+(?P<reading>\d+)'
                     r'\s+Writing:\s+(?P<writing>\d+)'
                     r'\s+Waiting:\s+(?P<waiting>\d+)')


class Nginx(base.HTTPStatsPlugin):

    DEFAULT_PATH = 'nginx_stub_status'
    GUID = 'com.meetme.newrelic_nginx_agent'

    GAUGES = ['connections', 'reading', 'writing', 'waiting']
    KEYS = {'connections': 'Totals/Connections',
            'requests': 'Totals/Requests',
            'accepts': 'Requests/Accepted',
            'handled': 'Requests/Handled',
            'time': 'Requests/Duration',
            'reading': 'Connections/Reading',
            'writing': 'Connections/Writing',
            'waiting': 'Connections/Waiting'}

    TYPES = {'connections': 'connections',
             'accepts': 'requests',
             'handled': 'requests',
             'requests': 'requests',
             'reading': 'connections',
             'time': 'seconds',
             'writing': 'connections',
             'waiting': 'connections'}

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
                    value = int(matches.group(key) or 0)
                except (IndexError, ValueError):
                    value = 0
                if key in self.GAUGES:
                    self.add_gauge_value(self.KEYS[key],
                                         self.TYPES[key],
                                         value)
                else:
                    self.add_derive_value(self.KEYS[key],
                                          self.TYPES[key],
                                          value)
        else:
            LOGGER.debug('Stats output: %r', stats)
