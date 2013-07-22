"""
uWSGI

"""
import json
import logging

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

    def fetch_data(self, connection):
        """Read the data from the socket

        :param  socket connection: The connection
        :return: dict

        """
        data = super(uWSGI, self).fetch_data(connection)
        if data:
            return json.loads(data)
        return {}

