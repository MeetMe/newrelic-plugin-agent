"""
Redis plugin polls Redis for stats

"""
import logging
import socket
import time

from newrelic_plugin_agent.plugins import base

LOGGER = logging.getLogger(__name__)


class Redis(base.Plugin):

    GUID = 'com.meetme.newrelic_redis_agent'

    DEFAULT_HOST = 'localhost'
    DEFAULT_PORT = 6379

    SOCKET_RECV_MAX = 32768

    def add_datapoints(self, server, stats):
        """Add all of the data points for a node

        :param dict stats: all of the nodes

        """
        self.add_gauge_value('Clients/Blocked', 'clients',
                             stats.get('blocked_clients', 0))
        self.add_gauge_value('Clients/Connected', 'clients',
                             stats.get('connected_clients', 0))
        self.add_gauge_value('Slaves/Connected', 'slaves',
                             stats.get('connected_slaves', 0))

        self.add_derive_value(self.name(server),
                              'Keys/Evicted', 'keys',
                              stats.get('evicted_keys', 0))
        self.add_derive_value(self.name(server),
                              'Keys/Expired', 'keys',
                              stats.get('expired_keys', 0))
        self.add_derive_value(self.name(server),
                              'Keys/Hit', 'requests',
                              stats.get('keyspace_hits', 0))
        self.add_derive_value(self.name(server),
                              'Keys/Missed', 'requests',
                              stats.get('keyspace_misses', 0))

        self.add_derive_value(self.name(server),
                              'Commands/Processed', 'cmds',
                              stats.get('total_commands_processed', 0))
        self.add_derive_value(self.name(server),
                              'Commands/Received', 'cmds',
                              stats.get('total_commands_received', 0))

        self.add_gauge_value('Pubsub/Commands', 'patterns',
                             stats.get('pubsub_commands', 0))

        self.add_gauge_value('Pubsub/Patterns', 'patterns',
                             stats.get('pubsub_patterns', 0))

        self.add_derive_value(self.name(server),
                              'System/CPU/User/Self', 'sec',
                              stats.get('used_cpu_user', 0))
        self.add_derive_value(self.name(server),
                              'System/CPU/User/Children',
                              'sec',
                              stats.get('used_cpu_user_children', 0))

        self.add_derive_value(self.name(server),
                              'System/CPU/System/Self', 'sec',
                              stats.get('used_cpu_sys', 0))
        self.add_derive_value(self.name(server),
                              'System/CPU/System/Children',
                              'sec',
                              stats.get('used_cpu_sys_children', 0))

        self.add_gauge_value('System/Memory', 'sec',
                             stats.get('used_memory', 0) / 1048576,
                             max_val=stats.get('used_memory_peak',
                                                0) / 1048576)
        self.add_gauge_value('System/Fragmentation', 'ratio',
                             stats.get('mem_fragmentation_ratio', 0))

        keys, expires = 0, 0
        for db in range(0, server.get('db_count', 16)):
            self.add_gauge_value('DB/%s/Expires' % db, 'keys',
                                 stats.get('db%i' % db,
                                           dict()).get('expires', 0))
            self.add_gauge_value('DB/%s/Keys' % db, 'keys',
                                 stats.get('db%i' % db, dict()).get('keys', 0))
            keys += stats.get('db%i' % db, dict()).get('keys', 0)
            expires += stats.get('db%i' % db, dict()).get('expires', 0)

        self.add_gauge_value('Keys/Total', 'keys', keys)
        self.add_gauge_value('Keys/Will Expire', 'keys', expires)

    def add_derive_value(self, key, metric_name, units, value):
        """Add a value that will derive the current value from the difference
        between the last interval value and the current value.

        If this is the first time a stat is being added, it will report a 0
        value until the next poll interval and it is able to calculate the
        derivative value.

        :param str key: The prefix for last interval stats
        :param str metric_name: The name of the metric
        :param str units: The unit type
        :param int value: The value to add

        """
        if key not in self.derive_last_interval:
            self.derive_last_interval[key] = dict()
        if value is None:
            value = 0
        metric = self.metric_name(metric_name, units)
        if metric not in self.derive_last_interval[key].keys():
            LOGGER.debug('Bypassing initial metric value for first run')
            self.derive[metric] = self.metric_payload(0)
        else:
            cval = value - self.derive_last_interval[key][metric]
            self.derive[metric] = self.metric_payload(cval)
        self.derive_last_interval[key][metric] = value
        LOGGER.debug('%s: %r %r', metric, self.derive[metric], value)

    def component_data(self, name):
        """Create the component section of the NewRelic Platform data payload
        message.

        :param str name: The server name
        :rtype: dict

        """
        metrics = dict()
        metrics.update(self.derive.items())
        metrics.update(self.gauge.items())
        metrics.update(self.rate.items())
        return {'name': name,
                'guid': self.GUID,
                'duration': self.poll_interval,
                'metrics': metrics}

    def connect(self, config):
        """Create a socket and connect it to the memcached daemon.

        :rtype: socket

        """
        connection = socket.socket()
        try:
            connection.connect((config.get('host', self.DEFAULT_HOST),
                                config.get('port', self.DEFAULT_PORT)))
        except socket.error as error:
            LOGGER.error('Error connecting to %s:%i - %s', error)
            return None
        return connection

    def fetch_data(self, connection):
        """Loop in and read in all the data until we have received it all.

        :param  socket connection: The connection
        :rtype: dict

        """
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
        self._values = list()
        self.consumers = 0

        # Fetch the data from Memcached
        for server in self.config:
            connection = self.connect(server)
            self.send_command(connection)
            self.add_datapoints(server, self.fetch_data(connection))
            self._values.append(self.component_data(self.name(server)))
            connection.close()
            del connection

        # Create all of the metrics
        LOGGER.info('Polling complete in %.2f seconds',
                    time.time() - start_time)

    def send_command(self, connection):
        """Send the command to get the statistics from the connection.

        :param socket connection: The connection

        """
        connection.send("*0\r\ninfo\r\n")

    def name(self, server):
        """Return the name of the server being processed or the local hostname

        :rtype: str

        """
        return server.get('name', socket.gethostname().split('.')[0])

    def values(self):
        """Return the poll results

        :rtype: dict

        """
        return self._values
