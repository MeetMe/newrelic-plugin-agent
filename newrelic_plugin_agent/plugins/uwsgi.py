"""
uWSGI

"""
import json
import logging
import re

from newrelic_plugin_agent.plugins import base

LOGGER = logging.getLogger(__name__)


class uWSGI(base.SocketStatsPlugin):

    GUID = 'com.meetme.newrelic_uwsgi_agent'

    DEFAULT_HOST = 'localhost'
    DEFAULT_PORT = 1717

    def add_datapoints(self, stats):
        """Add all of the data points for a node

        :param dict stats: all of the nodes

        """
        self.add_gauge_value('Listen Queue Size', 'connections',
                             stats.get('listen_queue', 0))
        self.add_gauge_value('Listen Queue Errors', 'errors',
                             stats.get('listen_queue_errors', 0))
        for lock in stats.get('locks', list()):
            lock_name = lock.keys()[0]
            self.add_gauge_value('Locks/%s' % lock_name, 'locks',
                                 lock[lock_name])

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
            harakiris += worker.get('harakiri_count', 0)
            requests += worker.get('requests', 0)
            respawns += worker.get('respawn_count', 0)
            signals += worker.get('signals', 0)

            # Add the per worker
            self.add_derive_value('Worker/%s/Exceptions' % id, 'exceptions',
                                  worker.get('exceptions', 0))
            self.add_derive_value('Worker/%s/Harakiri' % id, 'harakiris',
                                  worker.get('harakiri_count', 0))
            self.add_derive_value('Worker/%s/Requests' % id, 'requests',
                                  worker.get('requests', 0))
            self.add_derive_value('Worker/%s/Respawns' % id, 'respawns',
                                  worker.get('respawn_count', 0))
            self.add_derive_value('Worker/%s/Signals' % id, 'signals',
                                  worker.get('signals', 0))

            for app in worker['apps']:
                if app['id'] not in apps:
                    apps[app['id']] = {'exceptions': 0,
                                       'requests': 0}
                apps[app['id']]['exceptions'] += app['exceptions']
                apps[app['id']]['requests'] += app['requests']

        for app in apps:
            self.add_derive_value('Application/%s/Exceptions' % app,
                                  'exceptions',
                                  apps[app].get('exceptions', 0))
            self.add_derive_value('Application/%s/Requests' % app, 'requests',
                                  apps[app].get('requests', 0))

        self.add_derive_value('Summary/Applications', 'applications', len(apps))
        self.add_derive_value('Summary/Exceptions', 'exceptions', exceptions)
        self.add_derive_value('Summary/Harakiris', 'harakiris', harakiris)
        self.add_derive_value('Summary/Requests', 'requests', requests)
        self.add_derive_value('Summary/Respawns', 'respawns', respawns)
        self.add_derive_value('Summary/Signals', 'signals', signals)
        self.add_derive_value('Summary/Workers', 'workers',
                              len(stats.get('workers', ())))

    def fetch_data(self, connection):
        """Read the data from the socket

        :param  socket connection: The connection
        :return: dict

        """
        data = super(uWSGI, self).fetch_data(connection, read_till_empty=True)
        if data:
            data = re.sub(r'"HTTP_COOKIE=[^"]*"', '""', data)
            return json.loads(data)
        return {}

