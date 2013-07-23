"""
ApacheHTTPD Support

"""
import logging
import re

from newrelic_plugin_agent.plugins import base

LOGGER = logging.getLogger(__name__)

PATTERN = re.compile(r'^([\w\s{1}]+):\s([\d\.{1}]+)', re.M)


class ApacheHTTPD(base.HTTPStatsPlugin):

    DEFAULT_QUERY = 'auto'
    GUID = 'com.meetme.newrelic_apache_httpd_agent'
    KEYS = {'Total Accesses': {'type': '',
                               'label': 'Totals/Requests'},
            'BusyWorkers': {'type': 'gauge',
                            'label': 'Workers/Busy'},
            'Total kBytes': {'type': '',
                             'label': 'Totals/Bytes Sent',
                             'suffix': 'kb'},
            'BytesPerSec': {'type': 'gauge',
                            'label': 'Bytes/Per Second',
                            'suffix': 'bytes/sec'},
            'BytesPerReq': {'type': 'gauge',
                            'label': 'Requests/Average Payload Size',
                            'suffix': 'bytes'},
            'IdleWorkers': {'type': 'gauge', 'label': 'Workers/Idle'},
            'CPULoad': {'type': 'gauge', 'label': 'CPU Load'},
            'ReqPerSec': {'type': 'gauge', 'label': 'Requests/Velocity',
                                 'suffix': 'bytes/sec'},
            'Uptime': {'type': 'gauge', 'label': 'Uptime', 'suffix': 'sec'}}

    def error_message(self):
            LOGGER.error('Could not match any of the stats, please make ensure '
                         'Apache HTTPd is configured correctly. If you report '
                         'this as a bug, please include the full output of the '
                         'status page from %s in your ticket', self.stats_url)

    def add_datapoints(self, stats):
        """Add all of the data points for a node

        :param str stats: The stats content from Apache as a string

        """
        matches = PATTERN.findall(stats or '')
        for key, value in matches:

            try:
                value = int(value)
            except ValueError:
                try:
                    value = float(value)
                except ValueError:
                    value = 0

            if key in self.KEYS:
                if self.KEYS[key].get('type') == 'gauge':
                    self.add_gauge_value(self.KEYS[key]['label'],
                                         self.KEYS[key].get('suffix', ''),
                                         value)
                else:
                    self.add_derive_value(self.KEYS[key]['label'],
                                          self.KEYS[key].get('suffix', ''),
                                          value)
            else:
                LOGGER.warning('Found unmapped key/value pair: %s = %s',
                               key, value)
