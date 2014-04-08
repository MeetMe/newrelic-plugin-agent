"""
memcached

"""
import logging

from newrelic_plugin_agent.plugins import base

LOGGER = logging.getLogger(__name__)


class Memcached(base.SocketStatsPlugin):

    GUID = 'com.meetme.newrelic_memcached_agent'
    DEFAULT_PORT = 11211
    KEYS = ['curr_connections',
            'curr_items',
            'connection_structures',
            'cmd_get',
            'cmd_set',
            'cmd_flush',
            'get_hits',
            'get_misses',
            'delete_hits',
            'delete_misses',
            'incr_hits',
            'incr_misses',
            'decr_hits',
            'decr_misses',
            'cas_hits',
            'cas_misses',
            'cas_badval',
            'auth_cmds',
            'auth_errors',
            'bytes_read',
            'bytes_written',
            'bytes',
            'total_items',
            'evictions',
            'rusage_user',
            'conn_yields',
            'rusage_system']

    SOCKET_RECV_MAX = 32768

    def add_datapoints(self, stats):
        """Add all of the data points for a node

        :param dict stats: all of the nodes

        """
        self.command_value('CAS', 'cas', stats)
        self.add_derive_value('Command/Requests/Flush', 'flush',
                              stats['cmd_flush'])
        self.add_derive_value('Command/Errors/CAS', 'errors',
                              stats['cas_badval'])
        self.command_value('Decr', 'decr', stats)
        self.command_value('Delete', 'delete', stats)
        self.command_value('Get', 'get', stats)
        self.command_value('Incr', 'incr', stats)
        self.add_derive_value('Command/Requests/Set', '', stats['cmd_set'])

        self.add_gauge_value('Connection/Count', 'connections',
                             stats['curr_connections'])
        self.add_gauge_value('Connection/Structures', 'connection structures',
                             stats['connection_structures'])
        self.add_derive_value('Connection/Yields', 'yields',
                              stats['conn_yields'])
        self.add_derive_value('Evictions', 'items', stats['evictions'])
        self.add_gauge_value('Items', 'items', stats['curr_items'])

        self.add_derive_value('Network/In', 'bytes', stats['bytes_read'])
        self.add_derive_value('Network/Out', 'bytes', stats['bytes_written'])

        self.add_derive_value('System/CPU/System', 'seconds',
                              stats['rusage_user'])
        self.add_derive_value('System/CPU/User', 'seconds',
                              stats['rusage_user'])
        self.add_gauge_value('System/Memory', 'bytes', stats['bytes'])

    def command_value(self, name, prefix, stats):
        """Process commands adding the command and the hit ratio.

        :param str name: The command name
        :param str prefix: The command prefix
        :param dict stats: The request stats

        """
        total = stats['%s_hits' % prefix] + stats['%s_misses' % prefix]
        if total > 0:
            ratio = (float(stats['%s_hits' % prefix]) / float(total)) * 100
        else:
            ratio = 0
        self.add_derive_value('Command/Requests/%s' % name, 'requests', total)
        self.add_gauge_value('Command/Hit Ratio/%s' % name, 'ratio', ratio)

    def fetch_data(self, connection):
        """Loop in and read in all the data until we have received it all.

        :param  socket connection: The connection

        """
        connection.send("stats\n")
        data = super(Memcached, self).fetch_data(connection)
        data_in = []
        for line in data.replace('\r', '').split('\n'):
            if line == 'END':
                return self.process_data(data_in)
            data_in.append(line.strip())
        return None

    def process_data(self, data):
        """Loop through all the rows and parse each line, looking to see if it
        is in the data points we would like to process, adding the key => value
        pair to values if it is.

        :param list data: The list of rows
        :returns: dict

        """
        values = dict()
        for row in data:
            parts = row.split(' ')
            if parts[1] in self.KEYS:
                try:
                    values[parts[1]] = int(parts[2])
                except ValueError:
                    try:
                        values[parts[1]] = float(parts[2])
                    except ValueError:
                        LOGGER.warning('Could not parse line: %r', parts)
                        values[parts[1]] = 0

        # Back fill any missed data
        for key in self.KEYS:
            if key not in values:
                LOGGER.info('Populating missing element with 0: %s', key)
                values[key] = 0

        # Return the values dict
        return values
