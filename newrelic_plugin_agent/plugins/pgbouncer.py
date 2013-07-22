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

        self.add_gauge_value('Overview/Databases', '',
                             stats['LISTS']['databases'])
        self.add_gauge_value('Overview/Pools', '',
                             stats['LISTS']['pools'])
        self.add_gauge_value('Overview/Users', '',
                             stats['LISTS']['users'])

        self.add_gauge_value('Overview/Clients/Free', '',
                             stats['LISTS']['free_clients'])
        self.add_gauge_value('Overview/Clients/Used', '',
                             stats['LISTS']['used_clients'])
        self.add_gauge_value('Overview/Servers/Free', '',
                             stats['LISTS']['free_servers'])
        self.add_gauge_value('Overview/Servers/Used', '',
                             stats['LISTS']['used_servers'])

        for database in stats['STATS']:
            metric = 'Database/%s' % database['database']
            self.add_derive_value('%s/Query Time' % metric, 'sec',
                                  database['total_query_time'])
            self.add_derive_value('%s/Requests' % metric, '',
                                  database['total_requests'])
            self.add_derive_value('%s/Data Sent' % metric, 'bytes',
                                  database['total_sent'])
            self.add_derive_value('%s/Data Received' % metric, 'bytes',
                                  database['total_received'])

        for pool in stats['POOLS']:
            metric = 'Pools/%s' % pool['database']
            self.add_gauge_value('%s/Clients/Active' % metric, '',
                                 pool['cl_active'])
            self.add_gauge_value('%s/Clients/Waiting' % metric, '',
                                 pool['cl_waiting'])
            self.add_gauge_value('%s/Servers/Active' % metric, '',
                                 pool['sv_active'])
            self.add_gauge_value('%s/Servers/Idle' % metric, '',
                                 pool['sv_idle'])
            self.add_gauge_value('%s/Servers/Login' % metric, '',
                                 pool['sv_login'])
            self.add_gauge_value('%s/Servers/Tested' % metric, '',
                                 pool['sv_tested'])
            self.add_gauge_value('%s/Servers/Used' % metric, '',
                                 pool['sv_used'])
            self.add_gauge_value('%s/Maximum Wait' % metric, 'sec',
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
