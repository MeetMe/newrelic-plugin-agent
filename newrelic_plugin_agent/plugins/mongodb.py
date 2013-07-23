"""
MongoDB Support

"""
import datetime
from pymongo import errors
import logging
import pymongo

from newrelic_plugin_agent.plugins import base

LOGGER = logging.getLogger(__name__)


class MongoDB(base.Plugin):

    GUID = 'com.meetme.newrelic_mongodb_plugin_agent'

    def add_datapoints(self, name, stats):
        """Add all of the data points for a database

        :param str name: The name of the database for the stats
        :param dict stats: The stats data to add

        """
        base_key = 'Database/%s' % name
        self.add_gauge_value('%s/Extents' % base_key, '',
                             stats.get('extents', 0))
        self.add_gauge_value('%s/Size' % base_key, 'mb',
                             stats.get('dataSize', 0))
        self.add_gauge_value('%s/File Size' % base_key, 'mb',
                             stats.get('fileSize', 0))
        self.add_gauge_value('%s/Objects' % base_key, '',
                             stats.get('objects', 0))
        self.add_gauge_value('%s/Collections' % base_key, '',
                             stats.get('collections', 0))
        self.add_gauge_value('%s/Index/Count' % base_key, '',
                             stats.get('indexes', 0))
        self.add_gauge_value('%s/Index/Size' % base_key, 'bytes',
                             stats.get('indexSize', 0))

    def add_server_datapoints(self, stats):
        """Add all of the data points for a server

        :param dict stats: The stats data to add

        """
        asserts = stats.get('asserts', dict())
        self.add_derive_value('Asserts/Regular', '', asserts.get('regular', 0))
        self.add_derive_value('Asserts/Warning', '', asserts.get('warning', 0))
        self.add_derive_value('Asserts/Message', '', asserts.get('msg', 0))
        self.add_derive_value('Asserts/User', '', asserts.get('user', 0))
        self.add_derive_value('Asserts/Rollovers', '',
                              asserts.get('rollovers', 0))

        flush = stats.get('backgroundFlushing', dict())
        self.add_derive_timing_value('Background Flushes',
                                     'ms',
                                     flush.get('flushes', 0),
                                     flush.get('total_ms', 0),
                                     flush.get('last_ms', 0))
        self.add_gauge_value('Seconds since last flush',
                             'sec',
                             (datetime.datetime.now() -
                              flush.get('last_finished',
                                        datetime.datetime.now())).seconds)

        conn = stats.get('connections', dict())
        self.add_gauge_value('Connections/Available', '',
                             conn.get('available', 0))
        self.add_gauge_value('Connections/Current', '', conn.get('current', 0))

        cursors = stats.get('cursors', dict())
        self.add_gauge_value('Cursors/Open', '', cursors.get('totalOpen', 0))
        self.add_derive_value('Cursors/Timed Out', '', cursors.get('timedOut', 0))

        dur = stats.get('dur', dict())
        self.add_gauge_value('Durability/Commits in Write Lock', '',
                             dur.get('commitsInWriteLock', 0))
        self.add_gauge_value('Durability/Early Commits', '',
                             dur.get('earlyCommits', 0))
        self.add_gauge_value('Durability/Journal Commits', '',
                             dur.get('commits', 0))
        self.add_gauge_value('Durability/Journal MB Written', 'mb',
                             dur.get('journaledMB', 0))
        self.add_gauge_value('Durability/Data File MB Written', 'mb',
                             dur.get('writeToDataFilesMB', 0))

        timems = dur.get('timeMs', dict())
        self.add_gauge_value('Durability/Timings/Duration Measured', 'ms',
                             timems.get('dt', 0))
        self.add_gauge_value('Durability/Timings/Log Buffer Preparation', 'ms',
                             timems.get('prepLogBuffer', 0))
        self.add_gauge_value('Durability/Timings/Write to Journal', 'ms',
                             timems.get('writeToJournal', 0))
        self.add_gauge_value('Durability/Timings/Write to Data Files', 'ms',
                             timems.get('writeToDataFiles', 0))
        self.add_gauge_value('Durability/Timings/Remaping Private View', 'ms',
                             timems.get('remapPrivateView', 0))

        locks = stats.get('globalLock', dict())
        self.add_derive_value('Global Locks/Held', 'us',
                              locks.get('lockTime', 0))
        self.add_derive_value('Global Locks/Ratio', '',
                              locks.get('ratio', 0))

        active = locks.get('activeClients')
        self.add_derive_value('Global Locks/Active Clients/Total', '',
                              active.get('total', 0))
        self.add_derive_value('Global Locks/Active Clients/Readers', '',
                              active.get('readers', 0))
        self.add_derive_value('Global Locks/Active Clients/Writers', '',
                              active.get('writers', 0))

        queue = locks.get('currentQueue')
        self.add_derive_value('Global Locks/Queue/Total', '',
                              queue.get('total', 0))
        self.add_derive_value('Global Locks/Queue/Readers', '',
                              queue.get('readers', 0))
        self.add_derive_value('Global Locks/Queue/Writers', '',
                              queue.get('writers', 0))

        index = stats.get('indexCounters', dict())
        self.add_derive_value('Index/Accesses', '', index.get('accesses', 0))
        self.add_derive_value('Index/Hits', '', index.get('hits', 0))
        self.add_derive_value('Index/Misses', '', index.get('misses', 0))
        self.add_derive_value('Index/Resets', '', index.get('resets', 0))

        mem = stats.get('mem', dict())
        self.add_gauge_value('Memory/Mapped', 'mb',
                             mem.get('mapped', 0))
        self.add_gauge_value('Memory/Mapped with Journal', 'mb',
                             mem.get('mappedWithJournal', 0))
        self.add_gauge_value('Memory/Resident', 'mb',
                             mem.get('resident', 0))
        self.add_gauge_value('Memory/Virtual', 'mb',
                             mem.get('virtual', 0))

        net = stats.get('network', dict())
        self.add_derive_value('Network/Requests', '',
                              net.get('numRequests', 0))
        self.add_derive_value('Network/Transfer/In', 'bytes',
                              net.get('bytesIn', 0))
        self.add_derive_value('Network/Transfer/Out', 'bytes',
                              net.get('bytesOut', 0))

        ops = stats.get('opcounters', dict())
        self.add_derive_value('Operations/Insert', '', ops.get('insert', 0))
        self.add_derive_value('Operations/Query', '', ops.get('query', 0))
        self.add_derive_value('Operations/Update', '', ops.get('update', 0))
        self.add_derive_value('Operations/Delete', '', ops.get('delete', 0))
        self.add_derive_value('Operations/Get More', '', ops.get('getmore', 0))
        self.add_derive_value('Operations/Command', '', ops.get('command', 0))

        extra = stats.get('extra_info', dict())
        self.add_gauge_value('System/Heap Usage', 'bytes',
                             extra.get('heap_usage_bytes', 0))
        self.add_derive_value('System/Page Faults', '',
                              extra.get('page_faults', 0))

    def connect(self):
        return pymongo.MongoClient(self.config.get('host', 'localhost'),
                                   self.config.get('port', 27017))

    def get_and_add_stats(self):
        """Fetch the data from the MongoDB server and add the datapoints

        """
        databases = self.config.get('databases', list())
        if isinstance(databases, list):
            self.get_and_add_db_list(databases)
        else:
            self.get_and_add_db_with_auth(databases)

    def get_and_add_db_list(self, databases):
        """Handle the list of databases while supporting authentication for
        the admin if needed

        :param list databases: The database list

        """
        client = self.connect()
        for database in databases:
            db = client[database]
            try:
                if database == databases[0]:
                    if self.config.get('admin_username'):
                        db.authenticate(self.config['admin_username'],
                                        self.config.get('admin_password'))
                    self.add_server_datapoints(db.command('serverStatus'))
                self.add_datapoints(database, db.command('dbStats'))
            except errors.OperationFailure as error:
                LOGGER.critical('Could not fetch stats: %s', error)

    def get_and_add_db_with_auth(self, databases):
        """Handle the nested database structure with usernnames and password.

        :param dict databases: The databases data structure

        """
        client = self.connect()
        db_names = databases.keys()
        for database in db_names:
            db = client[database]
            try:
                if database == db_names[0]:
                    if self.config.get('admin_username'):
                        db.authenticate(self.config['admin_username'],
                                        self.config.get('admin_password'))
                    self.add_server_datapoints(db.command('serverStatus'))
                if 'username' in databases[database]:
                    db.authenticate(databases[database]['username'],
                                    databases[database].get('password'))
                self.add_datapoints(database, db.command('dbStats'))
            except errors.OperationFailure as error:
                LOGGER.critical('Could not fetch stats: %s', error)

    def poll(self):
        self.initialize()
        self.get_and_add_stats()
        self.finish()
