"""
HAProxy Support

"""
import logging
import re

from newrelic_plugin_agent.plugins import base

LOGGER = logging.getLogger(__name__)

PATTERN = re.compile(r'^current conns = (?P<connections>[1234567890]*);',re.MULTILINE|re.DOTALL)


class HAProxy(base.HTTPStatsPlugin):

    DEFAULT_PATH = 'haproxy?stats'
    GUID = 'com.meetme.newrelic_haproxy_agent'

    GAUGES = ['connections']
    KEYS = {'connections': 'Totals/Connections'}

    TYPES = {'connections': ''}

    def add_datapoints(self, stats):
        """Add all of the data points for a node

        :param str stats: The stub stats content

        """
        if not stats:
            return
        matches = PATTERN.search(stats)
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
