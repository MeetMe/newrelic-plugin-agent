"""
memcached

"""
import logging
import socket
import time

from newrelic_plugin_agent.plugins import base

LOGGER = logging.getLogger(__name__)


class Memcached(base.Plugin):

    GUID = 'com.meetme.newrelic_memcached_agent'

    DEFAULT_HOST = 'localhost'
    DEFAULT_PORT = 11211
    KEYS = ['curr_connections',
            'curr_items',
            'connection_struct',
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
        self.add_derive_value('Command/Requests/Flush', '', stats['cmd_flush'])
        self.add_derive_value('Command/Errors/CAS', '', stats['cas_badval'])
        self.command_value('Decr', 'decr', stats)
        self.command_value('Delete', 'delete', stats)
        self.command_value('Get', 'get', stats)
        self.command_value('Incr', 'incr', stats)
        self.add_derive_value('Command/Requests/Set', '', stats['cmd_set'])

        self.add_gauge_value('Connection/Count', '',
                             stats['curr_connections'])
        self.add_gauge_value('Connection/Structures', '',
                             stats['connection_struct'])
        self.add_derive_value('Connection/Yields', '',
                              stats['conn_yields'])
        self.add_derive_value('Evictions', '', stats['evictions'])
        self.add_gauge_value('Items', '', stats['curr_items'])

        self.add_derive_value('Network/In', 'bytes', stats['bytes_read'])
        self.add_derive_value('Network/Out', 'bytes', stats['bytes_written'])


        self.add_derive_value('System/CPU/System', 'sec', stats['rusage_user'])
        self.add_derive_value('System/CPU/User', 'sec', stats['rusage_user'])
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
        self.add_derive_value('Command/Requests/%s' % name, '', total)
        self.add_gauge_value('Command/Hit Ratio/%s' % name, '', ratio)

    def connect(self):
        """Create a socket and connect it to the memcached daemon.

        :rtype: socket

        """
        connection = socket.socket()
        try:
            connection.connect((self.config.get('host', self.DEFAULT_HOST),
                                self.config.get('port', self.DEFAULT_PORT)))
        except socket.error as error:
            LOGGER.error('Error connecting to %s:%i - %s', error)
            return None
        return connection

    def fetch_data(self, connection):
        """Loop in and read in all the data until we have received it all.

        :param  socket connection: The connection

        """
        # Loop while we get the data
        data_in = []
        while True:

            # Read in the data
            data = connection.recv(self.SOCKET_RECV_MAX)
            if not data:
                break

            # Iterate over each line that has been read in
            for line in data.replace('\r', '').split('\n'):
                # If we got END delimiter, exit
                if line == 'END':
                    return data_in

                # Append the line to our list
                data_in.append(line.strip())

    def poll(self):
        """This method is called after every sleep interval. If the intention
        is to use an IOLoop instead of sleep interval based daemon, override
        the run method.

        """
        LOGGER.info('Polling Memcached')
        start_time = time.time()

        # Initialize the values each iteration
        self.derive = dict()
        self.gauge = dict()
        self.rate = dict()
        self.consumers = 0

        # Fetch the data from Memcached
        connection = self.connect()
        self.send_command(connection)
        data = self.fetch_data(connection)
        connection.close()
        del connection

        # Create all of the metrics
        self.add_datapoints(self.process_data(data))
        LOGGER.info('Polling complete in %.2f seconds',
                    time.time() - start_time)

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
                LOGGER.warning('Populating missing element: %s', key)
                values[key] = 0

        # Return the values dict
        return values

    def send_command(self, connection):
        """Send the command to get the statistics from the connection.

        :param socket connection: The connection

        """
        connection.send("stats\n")
