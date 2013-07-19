"""
uWSGI

"""
import json
import logging
from os import path
import socket
import time

from newrelic_plugin_agent.plugins import base

LOGGER = logging.getLogger(__name__)


class UWSGI(base.Plugin):

    GUID = 'com.meetme.newrelic_uwsgi_agent'

    DEFAULT_HOST = 'localhost'
    DEFAULT_PORT = 1717

    SOCKET_RECV_MAX = 10485760

    def add_datapoints(self, stats):
        """Add all of the data points for a node

        :param dict stats: all of the nodes

        """
        self.add_gauge_value('Listen Queue Size', '',
                             stats.get('listen_queue', 0))
        self.add_gauge_value('Listen Queue Errors', '',
                             stats.get('listen_queue_errors', 0))
        for lock in stats.get('locks', list()):
            lock_name = lock.keys()[0]
            self.add_gauge_value('Locks/%s' % lock_name, '', lock[lock_name])

        exceptions = 0
        harakiris = 0
        requests = 0
        respawns = 0
        signals = 0

        apps = dict()

        for worker in stats.get('workers', list()):
            id = worker['id']

            # totals
            exceptions += worker.get('exceptions', 0)
            harakiris += worker.get('harakiris', 0)
            requests += worker.get('requests', 0)
            respawns += worker.get('respawns', 0)
            signals += worker.get('signals', 0)

            # Add the per worker
            self.add_derive_value('Worker/%s/Exceptions' % id, '',
                                  worker.get('exceptions', 0))
            self.add_derive_value('Worker/%s/Harakiri' % id, '',
                                  worker.get('harakiri_count', 0))
            self.add_derive_value('Worker/%s/Requests' % id, '',
                                  worker.get('requests', 0))
            self.add_derive_value('Worker/%s/Respawns' % id, '',
                                  worker.get('respawn_count', 0))
            self.add_derive_value('Worker/%s/Signals' % id, '',
                                  worker.get('signals', 0))

            for app in worker['apps']:
                if app['id'] not in apps:
                    apps[app['id']] = {'exceptions': 0,
                                       'requests': 0}
                apps[app['id']]['exceptions'] += app['exceptions']
                apps[app['id']]['requests'] += app['requests']

        for app in apps:
            self.add_derive_value('Application/%s/Exceptions' % app, '',
                                  apps[app].get('exceptions', 0))
            self.add_derive_value('Application/%s/Requests' % app, '',
                                  apps[app].get('requests', 0))

        self.add_derive_value('Summary/Applications', '', len(apps))
        self.add_derive_value('Summary/Exceptions', '', exceptions)
        self.add_derive_value('Summary/Harakiris', '', harakiris)
        self.add_derive_value('Summary/Requests', '', requests)
        self.add_derive_value('Summary/Respawns', '', respawns)
        self.add_derive_value('Summary/Signals', '', signals)
        self.add_derive_value('Summary/Workers', '',
                              len(stats.get('workers', ())))

    def connect(self):
        """Top level interface to create a socket and connect it to the
        uWSGI daemon.

        :rtype: socket

        """
        try:
            connection = self._connect()
        except socket.error as error:
            LOGGER.error('Error connecting to memcached: %s', error)
        else:
            return connection

    def _connect(self):
        """Low level interface to create a socket and connect it to the
        uWSGI daemon.

        :rtype: socket

        """
        if 'path' in self.config:
            if path.exists(self.config['path']):
                LOGGER.debug('Connecting to UNIX socket: %s',
                             self.config['path'])
                connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                connection.connect(self.config['path'])
            else:
                LOGGER.error('uWSGI UNIX socket path does not exist: %s',
                             self.config['path'])
        else:
            connection = socket.socket()
            connection.connect((self.config.get('host', self.DEFAULT_HOST),
                                self.config.get('port', self.DEFAULT_PORT)))
        return connection

    def fetch_data(self, connection):
        """Read the data from the socket

        :param  socket connection: The connection

        """
        LOGGER.debug('Fetching data')
        data = connection.recv(self.SOCKET_RECV_MAX)
        return json.loads(data)

    def poll(self):
        """This method is called after every sleep interval. If the intention
        is to use an IOLoop instead of sleep interval based daemon, override
        the run method.

        """
        LOGGER.info('Polling uWSGI')
        start_time = time.time()

        # Initialize the values each iteration
        self.derive = dict()
        self.gauge = dict()
        self.rate = dict()
        self.consumers = 0

        # Fetch the data from Memcached
        connection = self.connect()
        if not connection:
            LOGGER.error('Could not connect to uWSGI, skipping poll interval')
            return
        data = self.fetch_data(connection)
        connection.close()
        if data:
            # Create all of the metrics
            self.add_datapoints(data)
            LOGGER.info('Polling complete in %.2f seconds',
                        time.time() - start_time)
        else:
            LOGGER.error('Unsuccessful attempt to collect stats from uWSGI')
