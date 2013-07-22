"""
ApacheHTTPD Support

"""
import logging
import re

from newrelic_plugin_agent.plugins import base

LOGGER = logging.getLogger(__name__)

PATTERN = re.compile(r'Total Accesses\:\s(?P<accesses>\d+)\nTotal\skBytes\:'
                     r'\s(?P<bytes>\d+)\nCPULoad\:\s(?P<cpuload>[\.\de\-]+)\s'
                     r'Uptime\:\s(?P<uptime>\d+)\sReqPerSec\:\s'
                     r'(?P<requests_per_sec>[\d\.]+)\nBytesPerSec\:\s'
                     r'(?P<bytes_per_sec>[\d\.]+)\nBytesPerReq\:\s'
                     r'(?P<bytes_per_request>[\d\.]+)\nBusyWorkers\:\s'
                     r'(?P<busy>[\d\.]+)\nIdleWorkers\:\s(?P<idle>[\d\.]+)\n')

class ApacheHTTPD(base.HTTPStatsPlugin):

    DEFAULT_QUERY = 'auto'

    GUID = 'com.meetme.newrelic_apache_httpd_agent'

    GAUGES = ['busy', 'idle', 'bytes_per_request', 'bytes_per_sec',
              'uptime', 'cpuload', 'requests_per_sec']
    KEYS = {'accesses': 'Totals/Requests',
            'busy': 'Workers/Busy',
            'bytes': 'Totals/Bytes Sent',
            'bytes_per_sec': 'Bytes/Per Second',
            'bytes_per_request': 'Requests/Average Payload Size',
            'idle': 'Workers/Idle',
            'cpuload': 'CPU Load',
            'requests_per_sec': 'Requests/Velocity',
            'uptime': 'Uptime'}

    TYPES = {'bytes_per_sec': 'bytes/sec',
             'bytes_per_request': 'bytes',
             'bytes': 'kb',
             'uptime': 'sec',
             'busy': '',
             'idle': '',
             'cpuload': '',
             'requests_per_sec': 'requests/sec',
             'accesses': ''}

    def error_message(self):
            LOGGER.error('Could not match any of the stats, please make ensure '
                         'Apache HTTPd is configured correctly. If you report '
                         'this as a bug, please include the full output of the '
                         'status page from %s in your ticket', self.stats_url)

    def add_datapoints(self, stats):
        """Add all of the data points for a node

        :param str stats: The stats content from Apache as a string

        """
        matches = PATTERN.match(stats or '')
        if matches:
            for key in self.KEYS.keys():
                try:
                    value = int(matches.group(key))
                except (IndexError, ValueError):
                    try:
                        value = float(matches.group(key))
                    except (IndexError, ValueError):
                        value = 0
                if key in self.GAUGES:
                    self.add_gauge_value(self.KEYS[key], self.TYPES[key],
                                         value)
                else:
                    self.add_derive_value(self.KEYS[key], self.TYPES[key],
                                          value)
