"""
pgBouncer Plugin Support

"""
import psycopg2
from psycopg2 import extensions
from psycopg2 import extras

import logging
import time

from newrelic_plugin_agent.plugins import base

LOGGER = logging.getLogger(__name__)


class PgBouncer(base.Plugin):

    GUID = 'com.meetme.newrelic_pgbouncer_agent'
    MULTIROW = ['POOLS', 'STATS']

    def add_metrics(self, metrics):

        self.add_gauge_value('Overview/Databases', 'db',
                             metrics['LISTS']['databases'])
        self.add_gauge_value('Overview/Pools', 'pools',
                             metrics['LISTS']['pools'])
        self.add_gauge_value('Overview/Users', 'users',
                             metrics['LISTS']['users'])

        self.add_gauge_value('Overview/Clients/Free', 'connections',
                             metrics['LISTS']['free_clients'])
        self.add_gauge_value('Overview/Clients/Used', 'connections',
                             metrics['LISTS']['used_clients'])
        self.add_gauge_value('Overview/Servers/Free', 'connections',
                             metrics['LISTS']['free_servers'])
        self.add_gauge_value('Overview/Servers/Used', 'connections',
                             metrics['LISTS']['used_servers'])

        for database in metrics['STATS']:
            metric = 'Database/%s' % database['database']
            self.add_derive_value('%s/Query Time' % metric, 'sec',
                                  database['total_query_time'])
            self.add_derive_value('%s/Requests' % metric, 'requests',
                                  database['total_requests'])
            self.add_derive_value('%s/Data Sent' % metric, 'bytes',
                                  database['total_sent'])
            self.add_derive_value('%s/Data Received' % metric, 'bytes',
                                  database['total_received'])

        for pool in metrics['POOLS']:
            metric = 'Pools/%s' % pool['database']
            self.add_gauge_value('%s/Clients/Active' % metric, 'connections',
                                 pool['cl_active'])
            self.add_gauge_value('%s/Clients/Waiting' % metric, 'connections',
                                 pool['cl_waiting'])
            self.add_gauge_value('%s/Servers/Active' % metric, 'connections',
                                 pool['sv_active'])
            self.add_gauge_value('%s/Servers/Idle' % metric, 'connections',
                                 pool['sv_idle'])
            self.add_gauge_value('%s/Servers/Login' % metric, 'connections',
                                 pool['sv_login'])
            self.add_gauge_value('%s/Servers/Tested' % metric, 'connections',
                                 pool['sv_tested'])
            self.add_gauge_value('%s/Servers/Used' % metric, 'connections',
                                 pool['sv_used'])
            self.add_gauge_value('%s/Maximum Wait' % metric, 'sec',
                                 pool['maxwait'])

    @property
    def dsn(self):
        """Create a DSN to connect to

        :return str: The DSN to connect

        """
        dsn = "host='%(host)s' port=%(port)i dbname='pgbouncer' " \
              "user='%(user)s'" % self.config
        if self.config.get('password'):
            dsn += " password='%s'" % self.config['password']
        return dsn

    def connect(self):
        conn = psycopg2.connect(self.dsn)
        conn.set_isolation_level(extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        return conn

    def fetch_stats(self):
        conn = self.connect()
        cursor = conn.cursor(cursor_factory=extras.DictCursor)
        stats = dict()
        for key in self.MULTIROW:
            stats[key] = dict()
            cursor.execute('SHOW %s' % key)
            temp = cursor.fetchall()
            stats[key] = list()
            for row in temp:
                stats[key].append(dict(row))

        cursor.execute('SHOW LISTS')
        temp = cursor.fetchall()
        stats['LISTS'] = dict()
        for row in temp:
            stats['LISTS'][row['list']] = row['items']

        cursor.close()
        conn.close()
        return stats

    def poll(self):
        LOGGER.info('Polling pgBouncer at %(host)s:%(port)s', self.config)
        start_time = time.time()
        self.derive = dict()
        self.gauge = dict()
        self.rate = dict()
        self.add_metrics(self.fetch_stats())
        LOGGER.info('Polling complete in %.2f seconds',
                    time.time() - start_time)
