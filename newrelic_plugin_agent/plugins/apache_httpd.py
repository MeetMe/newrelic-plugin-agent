"""
ApacheHTTPD Support

"""
import logging
import re
import requests
import time

from newrelic_plugin_agent.plugins import base

LOGGER = logging.getLogger(__name__)

PATTERN = re.compile(r'Total Accesses\:\s(?P<accesses>\d+)\nTotal\skBytes\:'
                     r'\s(?P<bytes>\d+)\nCPULoad\:\s(?P<cpuload>[\.\d]+)\n'
                     r'Uptime\:\s(?P<uptime>\d+)\sReqPerSec\:\s'
                     r'(?P<requests_per_sec>[\d\.]+)\nBytesPerSec\:\s'
                     r'(?P<bytes_per_sec>[\d\.]+)\nBytesPerReq\:\s'
                     r'(?P<bytes_per_request>[\d\.]+)\nBusyWorkers\:\s'
                     r'(?P<busy>[\d\.]+)\nIdleWorkers\:\s(?P<idle>[\d\.]+)\n')

class ApacheHTTPD(base.Plugin):

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
             'busy': 'workers',
             'idle': 'workers',
             'cpuload': '%s',
             'requests_per_sec': 'requests/sec',
             'accesses': 'accesses'}

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

    @property
    def apache_stats_url(self):
        return 'http://%(host)s:%(port)s/%(path)s?auto' % self.config

    def fetch_data(self):
        """Fetch the data from the ApacheHTTPD server

        :rtype: str

        """
        try:
            response = requests.get(self.apache_stats_url)
        except requests.ConnectionError as error:
            LOGGER.error('Error polling ApacheHTTPD: %s', error)
            return {}

        if response.status_code == 200:
            try:
                return response.content
            except Exception as error:
                LOGGER.error('JSON decoding error: %r', error)
                return ''
        LOGGER.error('Error response from %s (%s): %s', self.apache_stats_url,
                     response.status_code, response.content)
        return ''

    def poll(self):
        LOGGER.info('Polling ApacheHTTPD via %s', self.apache_stats_url)
        start_time = time.time()
        self.derive = dict()
        self.gauge = dict()
        self.rate = dict()
        self.add_datapoints(self.fetch_data())
        LOGGER.info('Polling complete in %.2f seconds',
                    time.time() - start_time)
