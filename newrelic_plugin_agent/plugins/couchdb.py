"""
couchdb

"""
import logging
import requests
import time

from newrelic_plugin_agent.plugins import base

LOGGER = logging.getLogger(__name__)


class CouchDB(base.Plugin):

    GUID = 'com.meetme.newrelic_couchdb_agent'

    HTTP_METHODS = ['COPY', 'DELETE', 'GET', 'HEAD', 'POST', 'PUT']
    STATUS_CODES = [200, 201, 202, 301, 304, 400, 401,
                    403, 404, 405, 409, 412, 500]

    def add_datapoints(self, stats):
        """Add all of the data points for a node

        :param dict stats: all of the nodes

        """
        self.add_database_stats(stats['couchdb'])
        self.add_request_methods(stats['httpd_request_methods'])
        self.add_request_stats(stats['couchdb'], stats['httpd'])
        self.add_response_code_stats(stats['httpd_status_codes'])

    def add_database_stats(self, stats):
        self.add_gauge_value('Database/Open', 'dbs',
                             stats['open_databases'].get('current', 0),
                             stats['open_databases'].get('min', 0),
                             stats['open_databases'].get('max', 0))
        self.add_derive_value('Database/IO/Reads', 'ops',
                              stats['database_reads'].get('current', 0))
        self.add_derive_value('Database/IO/Writes', 'ops',
                              stats['database_writes'].get('current', 0))
        self.add_gauge_value('Files/Open', 'files',
                             stats['open_os_files'].get('current', 0),
                             stats['open_os_files'].get('min', 0),
                             stats['open_os_files'].get('max', 0))

    def add_request_stats(self, couchdb_stats, httpd_stats):
        self.add_derive_value('Requests/Processed', 'sec',
                              couchdb_stats['request_time'].get('current', 0))
        self.add_derive_value('Requests/Processed', 'requests',
                              httpd_stats['requests'].get('current', 0))
        self.add_derive_value('Requests/Bulk', 'requests',
                              httpd_stats['bulk_requests'].get('current', 0))
        self.add_derive_value('Requests/View', 'requests',
                              httpd_stats['view_reads'].get('current', 0))
        self.add_derive_value('Requests/Temporary View', 'requests',
                              httpd_stats['temporary_view_reads'].get('current',
                                                                      0))

    def add_request_methods(self, stats):
        for method in self.HTTP_METHODS:
            self.add_derive_value('Requests/Method/%s' % method, 'requests',
                                  stats[method].get('current', 0))

    def add_response_code_stats(self, stats):
        for code in self.STATUS_CODES:
            self.add_derive_value('Requests/Response/%s' % code, 'requests',
                                  stats[str(code)].get('current', 0))

    @property
    def couchdb_stats_url(self):
        return 'http://%(host)s:%(port)s/_stats' % self.config

    def fetch_data(self):
        """Fetch the data from the CouchDB server for the specified data type

        :rtype: dict

        """
        try:
            response = requests.get(self.couchdb_stats_url)
        except requests.ConnectionError as error:
            LOGGER.error('Error polling CouchDB: %s', error)
            return {}

        if response.status_code == 200:
            try:
                return response.json()
            except Exception as error:
                LOGGER.error('JSON decoding error: %r', error)
                return {}

        LOGGER.error('Error response from %s (%s): %s', self.couchdb_stats_url,
                     response.status_code, response.content)
        return {}

    def poll(self):
        LOGGER.info('Polling CouchDB via %s', self.couchdb_stats_url)
        start_time = time.time()
        self.derive = dict()
        self.gauge = dict()
        self.rate = dict()
        self.add_datapoints(self.fetch_data())
        LOGGER.info('Polling complete in %.2f seconds',
                    time.time() - start_time)
