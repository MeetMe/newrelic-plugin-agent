"""
PostgreSQL Plugin

"""
import logging
import psycopg2
from psycopg2 import extensions
from psycopg2 import extras

from newrelic_plugin_agent.plugins import base

LOGGER = logging.getLogger(__name__)

ARCHIVE = """SELECT CAST(COUNT(*) AS INT) AS file_count,
CAST(COALESCE(SUM(CAST(archive_file ~ $r$\.ready$$r$ as INT)), 0) AS INT)
AS ready_count,CAST(COALESCE(SUM(CAST(archive_file ~ $r$\.done$$r$ AS INT)),
0) AS INT) AS done_count FROM pg_catalog.pg_ls_dir('pg_xlog/archive_status')
AS archive_files (archive_file);"""
BACKENDS = """SELECT count(*) - ( SELECT count(*) FROM pg_stat_activity WHERE
current_query = '<IDLE>' ) AS backends_active, ( SELECT count(*) FROM
pg_stat_activity WHERE current_query = '<IDLE>' ) AS backends_idle
FROM pg_stat_activity;"""
BACKENDS_9_2 = """SELECT count(*) - ( SELECT count(*) FROM pg_stat_activity WHERE
state = 'idle' ) AS backends_active, ( SELECT count(*) FROM
pg_stat_activity WHERE state = 'idle' ) AS backends_idle
FROM pg_stat_activity;"""
TABLE_SIZE_ON_DISK = """SELECT ((sum(relpages)* 8) * 1024) AS
size_relations FROM pg_class WHERE relkind IN ('r', 't');"""
TABLE_COUNT = """SELECT count(1) as relations FROM pg_class WHERE
relkind IN ('r', 't');"""
INDEX_SIZE_ON_DISK = """SELECT ((sum(relpages)* 8) * 1024) AS
size_indexes FROM pg_class WHERE relkind = 'i';"""
INDEX_COUNT = """SELECT count(1) as indexes FROM pg_class WHERE
relkind = 'i';"""
TRANSACTIONS = """SELECT sum(xact_commit) AS transactions_committed,
sum(xact_rollback) AS transactions_rollback, sum(blks_read) AS blocks_read,
sum(blks_hit) AS blocks_hit, sum(tup_returned) AS tuples_returned,
sum(tup_fetched) AS tuples_fetched, sum(tup_inserted) AS tuples_inserted,
sum(tup_updated) AS tuples_updated, sum(tup_deleted) AS tuples_deleted
FROM pg_stat_database;"""
STATIO = """SELECT sum(heap_blks_read) AS heap_blocks_read, sum(heap_blks_hit)
AS heap_blocks_hit, sum(idx_blks_read) AS index_blocks_read, sum(idx_blks_hit)
AS index_blocks_hit, sum(toast_blks_read) AS toast_blocks_read,
sum(toast_blks_hit) AS toast_blocks_hit, sum(tidx_blks_read)
AS toastindex_blocks_read, sum(tidx_blks_hit) AS toastindex_blocks_hit
FROM pg_statio_all_tables WHERE schemaname <> 'pg_catalog';"""
BGWRITER = 'SELECT * FROM pg_stat_bgwriter;'
DATABASE = 'SELECT * FROM pg_stat_database;'
LOCKS = 'SELECT mode, count(mode) AS count FROM pg_locks ' \
        'GROUP BY mode ORDER BY mode;'

LOCK_MAP = {'AccessExclusiveLock': 'Locks/Access Exclusive',
            'AccessShareLock': 'Locks/Access Share',
            'ExclusiveLock': 'Locks/Exclusive',
            'RowExclusiveLock': 'Locks/Row Exclusive',
            'RowShareLock': 'Locks/Row Share',
            'ShareUpdateExclusiveLock': 'Locks/Update Exclusive Lock',
            'ShareLock': 'Locks/Share',
            'ShareRowExclusiveLock': 'Locks/Share Row Exclusive'}


class PostgreSQL(base.Plugin):

    GUID = 'com.meetme.newrelic_postgresql_agent'

    def add_stats(self, cursor):
        self.add_backend_stats(cursor)
        self.add_bgwriter_stats(cursor)
        self.add_database_stats(cursor)
        self.add_lock_stats(cursor)
        if self.config.get('relation_stats', True):
            self.add_index_stats(cursor)
            self.add_statio_stats(cursor)
            self.add_table_stats(cursor)
        self.add_transaction_stats(cursor)

        # add_wal_metrics needs superuser to get directory listings
        if self.config.get('superuser', True):
            self.add_wal_stats(cursor)

    def add_database_stats(self, cursor):
        cursor.execute(DATABASE)
        temp = cursor.fetchall()
        for row in temp:
            database = row['datname']
            self.add_gauge_value('Database/%s/Backends' % database, 'processes',
                                 row.get('numbackends', 0))
            self.add_derive_value('Database/%s/Transactions/Committed' %
                                  database, 'transactions',
                                  int(row.get('xact_commit', 0)))
            self.add_derive_value('Database/%s/Transactions/Rolled Back' %
                                  database, 'transactions',
                                  int(row.get('xact_rollback', 0)))
            self.add_derive_value('Database/%s/Tuples/Read from Disk' %
                                  database, 'tuples',
                                  int(row.get('blks_read', 0)))
            self.add_derive_value('Database/%s/Tuples/Read cache hit' %
                                  database, 'tuples',
                                  int(row.get('blks_hit', 0)))
            self.add_derive_value('Database/%s/Tuples/Returned/From Sequential '
                                  'Scan' % database, 'tuples',
                                  int(row.get('tup_returned', 0)))
            self.add_derive_value('Database/%s/Tuples/Returned/From Bitmap '
                                  'Scan' % database, 'tuples',
                                  int(row.get('tup_fetched', 0)))
            self.add_derive_value('Database/%s/Tuples/Writes/Inserts' %
                                  database, 'tuples',
                                  int(row.get('tup_inserted', 0)))
            self.add_derive_value('Database/%s/Tuples/Writes/Updates' %
                                  database, 'tuples',
                                  int(row.get('tup_updated', 0)))
            self.add_derive_value('Database/%s/Tuples/Writes/Deletes' %
                                  database, 'tuples',
                                  int(row.get('tup_deleted', 0)))
            self.add_derive_value('Database/%s/Conflicts' %
                                  database, 'tuples',
                                  int(row.get('conflicts', 0)))

    def add_backend_stats(self, cursor):
        if self.server_version < (9, 2, 0):
            cursor.execute(BACKENDS)
        else:
            cursor.execute(BACKENDS_9_2)
        temp = cursor.fetchone()
        self.add_gauge_value('Backends/Active', 'processes',
                             temp.get('backends_active', 0))
        self.add_gauge_value('Backends/Idle', 'processes',
                             temp.get('backends_idle', 0))

    def add_bgwriter_stats(self, cursor):
        cursor.execute(BGWRITER)
        temp = cursor.fetchone()
        self.add_derive_value('Background Writer/Checkpoints/Scheduled',
                              'checkpoints',
                              temp.get('checkpoints_timed', 0))
        self.add_derive_value('Background Writer/Checkpoints/Requested',
                              'checkpoints',
                              temp.get('checkpoints_requests', 0))

    def add_index_stats(self, cursor):
        cursor.execute(INDEX_COUNT)
        temp = cursor.fetchone()
        self.add_gauge_value('Objects/Indexes', 'indexes',
                             temp.get('indexes', 0))
        cursor.execute(INDEX_SIZE_ON_DISK)
        temp = cursor.fetchone()
        self.add_gauge_value('Disk Utilization/Indexes', 'bytes',
                             temp.get('size_indexes', 0))

    def add_lock_stats(self, cursor):
        cursor.execute(LOCKS)
        temp = cursor.fetchall()
        for lock in LOCK_MAP:
            found = False
            for row in temp:
                if row['mode'] == lock:
                    found = True
                    self.add_gauge_value(LOCK_MAP[lock], 'locks',
                                         int(row['count']))
            if not found:
                    self.add_gauge_value(LOCK_MAP[lock], 'locks', 0)

    def add_statio_stats(self, cursor):
        cursor.execute(STATIO)
        temp = cursor.fetchone()
        self.add_derive_value('IO Operations/Heap/Reads', 'iops',
                              int(temp.get('heap_blocks_read', 0)))
        self.add_derive_value('IO Operations/Heap/Hits', 'iops',
                              int(temp.get('heap_blocks_hit', 0)))
        self.add_derive_value('IO Operations/Index/Reads', 'iops',
                              int(temp.get('index_blocks_read', 0)))
        self.add_derive_value('IO Operations/Index/Hits', 'iops',
                              int(temp.get('index_blocks_hit', 0)))
        self.add_derive_value('IO Operations/Toast/Reads', 'iops',
                              int(temp.get('toast_blocks_read', 0)))
        self.add_derive_value('IO Operations/Toast/Hits', 'iops',
                              int(temp.get('toast_blocks_hit', 0)))
        self.add_derive_value('IO Operations/Toast Index/Reads', 'iops',
                              int(temp.get('toastindex_blocks_read', 0)))
        self.add_derive_value('IO Operations/Toast Index/Hits', 'iops',
                              int(temp.get('toastindex_blocks_hit', 0)))

    def add_table_stats(self, cursor):
        cursor.execute(TABLE_COUNT)
        temp = cursor.fetchone()
        self.add_gauge_value('Objects/Tables', 'tables',
                             temp.get('relations', 0))
        cursor.execute(TABLE_SIZE_ON_DISK)
        temp = cursor.fetchone()
        self.add_gauge_value('Disk Utilization/Tables', 'bytes',
                             temp.get('size_relations', 0))

    def add_transaction_stats(self, cursor):
        cursor.execute(TRANSACTIONS)
        temp = cursor.fetchone()
        self.add_derive_value('Transactions/Committed', 'transactions',
                              int(temp.get('transactions_committed', 0)))
        self.add_derive_value('Transactions/Rolled Back', 'transactions',
                              int(temp.get('transactions_rollback', 0)))

        self.add_derive_value('Tuples/Read from Disk', 'tuples',
                              int(temp.get('blocks_read', 0)))
        self.add_derive_value('Tuples/Read cache hit', 'tuples',
                              int(temp.get('blocks_hit', 0)))

        self.add_derive_value('Tuples/Returned/From Sequential Scan',
                              'tuples',
                              int(temp.get('tuples_returned', 0)))
        self.add_derive_value('Tuples/Returned/From Bitmap Scan',
                              'tuples',
                              int(temp.get('tuples_fetched', 0)))

        self.add_derive_value('Tuples/Writes/Inserts', 'tuples',
                              int(temp.get('tuples_inserted', 0)))
        self.add_derive_value('Tuples/Writes/Updates', 'tuples',
                              int(temp.get('tuples_updated', 0)))
        self.add_derive_value('Tuples/Writes/Deletes', 'tuples',
                              int(temp.get('tuples_deleted', 0)))

    def add_wal_stats(self, cursor):
        cursor.execute(ARCHIVE)
        temp = cursor.fetchone()
        self.add_derive_value('Archive Status/Total', 'files',
                              temp.get('file_count', 0))
        self.add_gauge_value('Archive Status/Ready', 'files',
                             temp.get('ready_count', 0))
        self.add_derive_value('Archive Status/Done', 'files',
                              temp.get('done_count', 0))


    def connect(self):
        """Connect to PostgreSQL, returning the connection object.

        :rtype: psycopg2.connection

        """
        conn = psycopg2.connect(**self.connection_arguments)
        conn.set_isolation_level(extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        return conn

    @property
    def connection_arguments(self):
        """Create connection parameter dictionary for psycopg2.connect

        :return dict: The dictionary to be passed to psycopg2.connect
            via double-splat
        """
        filtered_args = ["name", "superuser", "relation_stats"]
        args = {}
        for key in set(self.config) - set(filtered_args):
            if key == 'dbname':
                args['database'] = self.config[key]
            else:
                args[key] = self.config[key]
        return args

    def poll(self):
        self.initialize()
        try:
            self.connection = self.connect()
        except psycopg2.OperationalError as error:
            LOGGER.critical('Could not connect to %s, skipping stats run: %s',
                            self.__class__.__name__, error)
            return
        cursor = self.connection.cursor(cursor_factory=extras.DictCursor)
        self.add_stats(cursor)
        cursor.close()
        self.connection.close()
        self.finish()

    @property
    def server_version(self):
        """Return connection server version in PEP 369 format

        :returns: tuple

        """
        return (self.connection.server_version % 1000000 / 10000,
                self.connection.server_version % 10000 / 100,
                self.connection.server_version % 100)
