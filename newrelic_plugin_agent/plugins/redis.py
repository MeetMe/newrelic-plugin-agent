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
        self.add_gauge_value('Clients/Blocked', 'clients',
                             stats.get('blocked_clients', 0))
        self.add_gauge_value('Clients/Connected', 'clients',
                             stats.get('connected_clients', 0))
        self.add_gauge_value('Slaves/Connected', 'slaves',
                             stats.get('connected_slaves', 0))
        self.add_gauge_value('Last master IO sync (lag time)', 'seconds',
                             stats.get('master_last_io_seconds_ago', 0))

        # must happen before saving the new values
        # but only if we have the previous values
        if ('Keys/Hit' in self.derive_last_interval.keys() and
                'Keys/Missed' in self.derive_last_interval.keys()):
            prev_hits = self.derive_last_interval['Keys/Hit']
            prev_misses = self.derive_last_interval['Keys/Missed']

            # hits and misses since the last measure
            hits = stats.get('keyspace_hits', 0) - prev_hits
            misses = stats.get('keyspace_misses', 0) - prev_misses

            # total queries since the last measure
            total = hits + misses

            if total > 0:
                self.add_gauge_value('Hits Ratio', 'ratio', 100 * hits / total)

        self.add_derive_value('Evictions', 'keys',
                              stats.get('evicted_keys', 0))
        self.add_derive_value('Expirations', 'keys',
                              stats.get('expired_keys', 0))
        self.add_derive_value('Keys Hit', 'keys',
                              stats.get('keyspace_hits', 0))
        self.add_derive_value('Keys Missed', 'keys',
                              stats.get('keyspace_misses', 0))

        self.add_derive_value('Commands Processed', 'commands',
                              stats.get('total_commands_processed', 0))
        self.add_derive_value('Connections', 'connections',
                              stats.get('total_connections_received', 0))
        self.add_derive_value('Changes Since Last Save', 'changes',
                              stats.get('rdb_changes_since_last_save', 0))
        self.add_derive_value('Last Save Time', 'seconds',
                              stats.get('rdb_last_bgsave_time_sec', 0))

        self.add_gauge_value('Pubsub/Commands', 'commands',
                             stats.get('pubsub_commands', 0))
        self.add_gauge_value('Pubsub/Patterns', 'patterns',
                             stats.get('pubsub_patterns', 0))

        self.add_derive_value('CPU/User/Self', 'seconds',
                              stats.get('used_cpu_user', 0))
        self.add_derive_value('CPU/System/Self', 'seconds',
                              stats.get('used_cpu_sys', 0))

        self.add_derive_value('CPU/User/Children', 'seconds',
                              stats.get('used_cpu_user_childrens', 0))

        self.add_derive_value('CPU/System/Children', 'seconds',
                              stats.get('used_cpu_sys_childrens', 0))

        self.add_gauge_value('Memory Use', 'bytes',
                             stats.get('used_memory', 0),
                             max_val=stats.get('used_memory_peak', 0 ))
        self.add_gauge_value('Memory Fragmentation', 'ratio',
                             stats.get('mem_fragmentation_ratio', 0))

        keys, expires = 0, 0
        for db in range(0, self.config.get('db_count', 16)):

            db_stats = stats.get('db%i' % db, dict())
            self.add_gauge_value('DB/%s/Expires' % db, 'keys',
                                db_stats.get('expires', 0))
            self.add_gauge_value('DB/%s/Keys' % db, 'keys',
                                 db_stats.get('keys', 0))
            keys += db_stats.get('keys', 0)
            expires += db_stats.get('expires', 0)

        self.add_gauge_value('Keys/Total', 'keys', keys)
        self.add_gauge_value('Keys/Will Expire', 'keys', expires)

    def connect(self):
        """Top level interface to create a socket and connect it to the
        redis daemon.

        :rtype: socket

        """
        connection = super(Redis, self).connect()
        if connection and self.config.get('password'):
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
                key, value = line.strip().split(':',1)
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
