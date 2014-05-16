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
                               'label': 'Totals/Requests',
                               'suffix': 'requests'},
            'BusyWorkers': {'type': 'gauge',
                            'label': 'Workers/Busy',
                            'suffix': 'workers'},
            'Total kBytes': {'type': '',
                             'label': 'Totals/Bytes Sent',
                             'suffix': 'kb'},
            'BytesPerSec': {'type': 'gauge',
                            'label': 'Bytes/Per Second',
                            'suffix': 'bytes/sec'},
            'BytesPerReq': {'type': 'gauge',
                            'label': 'Requests/Average Payload Size',
                            'suffix': 'bytes'},
            'IdleWorkers': {'type': 'gauge', 'label': 'Workers/Idle',
                            'suffix': 'workers'},
            'CPULoad': {'type': 'gauge', 'label': 'CPU Load',
                        'suffix': 'processes'},
            'ReqPerSec': {'type': 'gauge', 'label': 'Requests/Velocity',
                          'suffix': 'requests/sec'},
            'Uptime': {'type': 'gauge', 'label': 'Uptime', 'suffix': 'sec'},
            'ConnsTotal': {'type': 'gauge', 'label': 'Connections/Total', 'suffix': 'conns'},
            'ConnsAsyncWriting': {'type': 'gauge', 'label': 'Connections/AsyncWriting', 'suffix': 'conns'},
            'ConnsAsyncKeepAlive': {'type': 'gauge', 'label': 'Connections/AsyncKeepAlive', 'suffix': 'conns'},
            'ConnsAsyncClosing': {'type': 'gauge', 'label': 'Connections/AsyncClosing', 'suffix': 'conns'},
            '_': {'type': 'gauge', 'label': 'Scoreboard/Waiting For Conn', 'suffix': 'slots'},
            'S': {'type': 'gauge', 'label': 'Scoreboard/Starting Up', 'suffix': 'slots'},
            'R': {'type': 'gauge', 'label': 'Scoreboard/Reading Request', 'suffix': 'slots'},
            'W': {'type': 'gauge', 'label': 'Scoreboard/Sending Reply', 'suffix': 'slots'},
            'K': {'type': 'gauge', 'label': 'Scoreboard/Keepalive Read', 'suffix': 'slots'},
            'D': {'type': 'gauge', 'label': 'Scoreboard/DNS Lookup', 'suffix': 'slots'},
            'C': {'type': 'gauge', 'label': 'Scoreboard/Closing Conn', 'suffix': 'slots'},
            'L': {'type': 'gauge', 'label': 'Scoreboard/Logging', 'suffix': 'slots'},
            'G': {'type': 'gauge', 'label': 'Scoreboard/Gracefully Finishing', 'suffix': 'slots'},
            'I': {'type': 'gauge', 'label': 'Scoreboard/Idle Cleanup', 'suffix': 'slots'},
            '.': {'type': 'gauge', 'label': 'Scoreboard/Open Slot', 'suffix': 'slots'}}

    def error_message(self):
        LOGGER.error('Could not match any of the stats, please make ensure '
                     'Apache HTTPd is configured correctly. If you report '
                     'this as a bug, please include the full output of the '
                     'status page from %s in your ticket', self.stats_url)

    def get_scoreboard(self, data):
        """Fetch the scoreboard from the stats URL

        :rtype: str

        """
        keys = ['_', 'S', 'R', 'W', 'K', 'D', 'C', 'L', 'G', 'I', '.']
        values = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        score_out = dict(zip(keys, values))

        for line in data.splitlines():
            if line.find('Scoreboard') != -1:
                scoreboard = line.replace('Scoreboard: ','')
                for i in range(0, len(scoreboard)):
                    score_out[scoreboard[i]] += 1
        return score_out

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
                LOGGER.debug('Found unmapped key/value pair: %s = %s',
                             key, value)
        
        score_data = self.get_scoreboard(stats)
        for key, value in score_data.iteritems():
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
                LOGGER.debug('Found unmapped key/value pair: %s = %s',
                             key, value)

