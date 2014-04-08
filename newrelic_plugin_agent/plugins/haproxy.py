"""
HAProxy Support

"""
import logging

from newrelic_plugin_agent.plugins import base

LOGGER = logging.getLogger(__name__)


class HAProxy(base.CSVStatsPlugin):

    DEFAULT_PATH = 'haproxy?stats;csv'
    GUID = 'com.meetme.newrelic_haproxy_agent'
    UNIT = {'Queue': {'Current': 'connections', 'Max': 'connections'},
            'Sessions': {'Current': 'sessions', 'Max': 'sessions',
                         'Total': 'sessions'},
            'Denied': {'Request': 'requests', 'Response': 'responses'},
            'Errors': {'Request': 'requests', 'Response': 'responses',
                       'Connections': 'connections'},
            'Warnings': {'Retry': 'retries', 'Redispatch': 'redispatches'},
            'Server': {'Downtime': 'ms'},
            'Bytes': {'In': 'bytes', 'Out': 'bytes'}}

    def sum_data(self, stats):
        """Return the summed data as a dict

        :rtype: dict

        """
        data = {'Queue': {'Current': 0, 'Max': 0},
                'Sessions': {'Current': 0, 'Max': 0, 'Total': 0},
                'Bytes': {'In': 0, 'Out': 0},
                'Denied': {'Request': 0, 'Response': 0},
                'Errors': {'Request': 0, 'Response': 0, 'Connections': 0},
                'Warnings': {'Retry': 0, 'Redispatch': 0},
                'Server': {'Downtime': 0}}
        for row in stats:
            data['Queue']['Current'] += int(row.get('qcur') or 0)
            data['Queue']['Max'] += int(row.get('qmax') or 0)
            data['Sessions']['Current'] += int(row.get('scur') or 0)
            data['Sessions']['Max'] += int(row.get('smax') or 0)
            data['Sessions']['Total'] += int(row.get('stot') or 0)
            data['Bytes']['In'] += int(row.get('bin') or 0)
            data['Bytes']['Out'] += int(row.get('bout') or 0)
            data['Denied']['Request'] += int(row.get('dreq') or 0)
            data['Denied']['Response'] += int(row.get('dresp') or 0)
            data['Errors']['Request'] += int(row.get('ereq') or 0)
            data['Errors']['Response'] += int(row.get('eresp') or 0)
            data['Errors']['Connections'] += int(row.get('econ') or 0)
            data['Warnings']['Retry'] += int(row.get('wretr') or 0)
            data['Warnings']['Redispatch'] += int(row.get('wredis') or 0)
            data['Server']['Downtime'] += int(row.get('downtime') or 0)
        return data

    def add_datapoints(self, stats):
        """Add all of the data points for a node

        :param list stats: The parsed csv content

        """
        if not stats:
            return
        stats = self.sum_data(stats)

        for section in [key for key in stats.keys() if key != 'server']:
            for key in stats[section].keys():
                self.add_derive_value('%s/%s' % (section, key),
                                      self.UNIT.get(section,
                                                    dict()).get(key, ''),
                                      stats[section][key])
        self.add_gauge_value('Server/Downtime', 'ms',
                             stats['Server']['Downtime'])
