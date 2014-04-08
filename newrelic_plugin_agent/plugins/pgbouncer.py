"""
pgBouncer Plugin Support

"""
import logging

from newrelic_plugin_agent.plugins import postgresql

LOGGER = logging.getLogger(__name__)


class PgBouncer(postgresql.PostgreSQL):

    GUID = 'com.meetme.newrelic_pgbouncer_agent'
    MULTIROW = ['POOLS', 'STATS']

    def add_pgbouncer_stats(self, stats):

        self.add_gauge_value('Overview/Databases', 'databases',
                             stats['LISTS']['databases'])
        self.add_gauge_value('Overview/Pools', 'pools',
                             stats['LISTS']['pools'])
        self.add_gauge_value('Overview/Users', 'users',
                             stats['LISTS']['users'])

        self.add_gauge_value('Overview/Clients/Free', 'clients',
                             stats['LISTS']['free_clients'])
        self.add_gauge_value('Overview/Clients/Used', 'clients',
                             stats['LISTS']['used_clients'])
        self.add_gauge_value('Overview/Servers/Free', 'servers',
                             stats['LISTS']['free_servers'])
        self.add_gauge_value('Overview/Servers/Used', 'servers',
                             stats['LISTS']['used_servers'])

        requests = 0
        for database in stats['STATS']:
            metric = 'Database/%s' % database['database']
            self.add_derive_value('%s/Query Time' % metric, 'seconds',
                                  database['total_query_time'])
            self.add_derive_value('%s/Requests' % metric, 'requests',
                                  database['total_requests'])
            self.add_derive_value('%s/Data Sent' % metric, 'bytes',
                                  database['total_sent'])
            self.add_derive_value('%s/Data Received' % metric, 'bytes',
                                  database['total_received'])
            requests += database['total_requests']

        self.add_derive_value('Overview/Requests', 'requests', requests)

        for pool in stats['POOLS']:
            metric = 'Pools/%s' % pool['database']
            self.add_gauge_value('%s/Clients/Active' % metric, 'clients',
                                 pool['cl_active'])
            self.add_gauge_value('%s/Clients/Waiting' % metric, 'clients',
                                 pool['cl_waiting'])
            self.add_gauge_value('%s/Servers/Active' % metric, 'servers',
                                 pool['sv_active'])
            self.add_gauge_value('%s/Servers/Idle' % metric, 'servers',
                                 pool['sv_idle'])
            self.add_gauge_value('%s/Servers/Login' % metric, 'servers',
                                 pool['sv_login'])
            self.add_gauge_value('%s/Servers/Tested' % metric, 'servers',
                                 pool['sv_tested'])
            self.add_gauge_value('%s/Servers/Used' % metric, 'servers',
                                 pool['sv_used'])
            self.add_gauge_value('%s/Maximum Wait' % metric, 'seconds',
                                 pool['maxwait'])

    def add_stats(self, cursor):
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

        self.add_pgbouncer_stats(stats)

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
