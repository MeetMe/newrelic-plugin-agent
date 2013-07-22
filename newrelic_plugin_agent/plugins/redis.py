"""
Redis plugin polls Redis for stats

"""
import logging

from newrelic_plugin_agent.plugins import base

LOGGER = logging.getLogger(__name__)


class Redis(base.SocketStatsPlugin):

    GUID = 'com.meetme.newrelic_redis_agent'

    DEFAULT_PORT = 6379

    def add_datapoints(self, stats):
        """Add all of the data points for a node

        :param dict stats: all of the nodes

        """
        self.add_gauge_value('Clients/Blocked', '',
                             stats.get('blocked_clients', 0))
        self.add_gauge_value('Clients/Connected', '',
                             stats.get('connected_clients', 0))
        self.add_gauge_value('Slaves/Connected', '',
                             stats.get('connected_slaves', 0))

        self.add_derive_value('Keys/Evicted', '',
                              stats.get('evicted_keys', 0))
        self.add_derive_value('Keys/Expired', '',
                              stats.get('expired_keys', 0))
        self.add_derive_value('Keys/Hit', '',
                              stats.get('keyspace_hits', 0))
        self.add_derive_value('Keys/Missed', '',
                              stats.get('keyspace_misses', 0))

        self.add_derive_value('Commands Processed', '',
                              stats.get('total_commands_processed', 0))
        self.add_derive_value('Connections', '',
                              stats.get('total_connections_received', 0))
        self.add_derive_value('Changes Since Last Save', '',
                              stats.get('changes_since_last_save', 0))

        self.add_gauge_value('Pubsub/Commands', '',
                             stats.get('pubsub_commands', 0))
        self.add_gauge_value('Pubsub/Patterns', '',
                             stats.get('pubsub_patterns', 0))

        self.add_derive_value('CPU/User/Self', 'sec',
                              stats.get('used_cpu_user', 0))
        self.add_derive_value('CPU/System/Self', 'sec',
                              stats.get('used_cpu_sys', 0))

        self.add_derive_value('CPU/User/Children', 'sec',
                              stats.get('used_cpu_user_childrens', 0))

        self.add_derive_value('CPU/System/Children', 'sec',
                              stats.get('used_cpu_sys_childrens', 0))

        self.add_gauge_value('Memory Use', 'MB',
                             stats.get('used_memory', 0) / 1048576,
                             max_val=stats.get('used_memory_peak',
                                                0) / 1048576)
        self.add_gauge_value('Memory Fragmentation', 'ratio',
                             stats.get('mem_fragmentation_ratio', 0))

        keys, expires = 0, 0
        for db in range(0, self.config.get('db_count', 16)):

            db_stats = stats.get('db%i' % db, dict())
            self.add_gauge_value('DB/%s/Expires' % db, '',
                                db_stats.get('expires', 0))
            self.add_gauge_value('DB/%s/Keys' % db, '',
                                 db_stats.get('keys', 0))
            keys += db_stats.get('keys', 0)
            expires += db_stats.get('expires', 0)

        self.add_gauge_value('Keys/Total', '', keys)
        self.add_gauge_value('Keys/Will Expire', '', expires)

    def connect(self):
        """Top level interface to create a socket and connect it to the
        memcached daemon.

        :rtype: socket

        """
        connection = super(Redis, self).connect()
        if self.config.get('password'):
            connection.send("*2\r\n$4\r\nAUTH\r\n$%i\r\n%s\r\n" %
                            (len(self.config['password']),
                             self.config['password']))
            buffer_value = connection.recv(self.SOCKET_RECV_MAX)
            if buffer_value == '+OK\r\n':
                return connection
            LOGGER.error('Authentication error: %s', buffer_value[4:].strip())
            return None
        return connection

    def fetch_data(self, connection):
        """Loop in and read in all the data until we have received it all.

        :param  socket connection: The connection
        :rtype: dict

        """
        connection.send("*0\r\ninfo\r\n")

        # Read in the first line $1437
        buffer_value = connection.recv(self.SOCKET_RECV_MAX)
        lines = buffer_value.split('\r\n')

        if lines[0][0] == '$':
            byte_size = int(lines[0][1:].strip())
        else:
            return None

        while len(buffer_value) < byte_size:
            buffer_value += connection.recv(self.SOCKET_RECV_MAX)

        lines = buffer_value.split('\r\n')
        values = dict()
        for line in lines:
            if ':' in line:
                key, value = line.strip().split(':')
                if key[:2] == 'db':
                    values[key] = dict()
                    subvalues = value.split(',')
                    for temp in subvalues:
                        subvalue = temp.split('=')
                        value = subvalue[-1]
                        try:
                            values[key][subvalue[0]] = int(value)
                        except ValueError:
                            try:
                                values[key][subvalue[0]] = float(value)
                            except ValueError:
                                values[key][subvalue[0]] = value
                    continue
                try:
                    values[key] = int(value)
                except ValueError:
                    try:
                        values[key] = float(value)
                    except ValueError:
                        values[key] = value
        return values
