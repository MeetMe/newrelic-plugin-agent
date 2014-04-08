"""
CouchDB

"""
import logging

from newrelic_plugin_agent.plugins import base

LOGGER = logging.getLogger(__name__)


class CouchDB(base.JSONStatsPlugin):

    DEFAULT_PATH = '/_stats'
    GUID = 'com.meetme.newrelic_couchdb_agent'

    HTTP_METHODS = ['COPY', 'DELETE', 'GET', 'HEAD', 'POST', 'PUT']
    STATUS_CODES = [200, 201, 202, 301, 304, 400, 401,
                    403, 404, 405, 409, 412, 500]

    def add_datapoints(self, stats):
        """Add all of the data points for a node

        :param dict stats: all of the nodes

        """
        LOGGER.debug('Stats: %r', stats)
        self.add_database_stats(stats['couchdb'])
        self.add_request_methods(stats['httpd_request_methods'])
        self.add_request_stats(stats['couchdb'], stats['httpd'])
        self.add_response_code_stats(stats['httpd_status_codes'])

    def add_database_stats(self, stats):
        self.add_gauge_value('Database/Open', 'dbs',
                             stats['open_databases'].get('current', 0),
                             stats['open_databases'].get('min', 0),
                             stats['open_databases'].get('max', 0))
        self.add_derive_value('Database/IO/Reads', 'iops',
                              stats['database_reads'].get('current', 0))
        self.add_derive_value('Database/IO/Writes', 'iops',
                              stats['database_writes'].get('current', 0))
        self.add_gauge_value('Files/Open', 'files',
                             stats['open_os_files'].get('current', 0),
                             stats['open_os_files'].get('min', 0),
                             stats['open_os_files'].get('max', 0))

    def add_request_stats(self, couchdb, httpd):
        self.add_derive_value('Requests/Duration', 'seconds',
                              couchdb['request_time'].get('current', 0))
        self.add_derive_value('Requests/Type/Document', 'requests',
                              httpd['requests'].get('current', 0))
        self.add_derive_value('Requests/Type/Bulk', 'requests',
                              httpd['bulk_requests'].get('current', 0))
        self.add_derive_value('Requests/Type/View', 'requests',
                              httpd['view_reads'].get('current', 0))
        self.add_derive_value('Requests/Type/Temporary View', 'requests',
                              httpd['temporary_view_reads'].get('current', 0))

    def add_request_methods(self, stats):
        for method in self.HTTP_METHODS:
            self.add_derive_value('Requests/Method/%s' % method, 'requests',
                                  stats[method].get('current', 0))

    def add_response_code_stats(self, stats):
        for code in self.STATUS_CODES:
            self.add_derive_value('Requests/Response/%s' % code, 'requests',
                                  stats[str(code)].get('current', 0))
