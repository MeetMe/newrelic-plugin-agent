"""
Edgecast Plugin Agent

"""
import logging
import requests
import time

from newrelic_plugin_agent.plugins import base

LOGGER = logging.getLogger(__name__)


class Edgecast(base.Plugin):

    GUID = 'com.meetme.newrelic_edgecast_agent'

    CACHE_FIELDS = {'TCP_EXPIRED_HIT': {'name': 'Expired Items',
                                        'unit': 'hit/sec'},
                    'TCP_EXPIRED_MISS': {'name': 'Expired Items',
                                         'unit': 'miss/sec'},
                    'TCP_HIT': {'name': 'Items', 'unit': 'hit/sec'},
                    'TCP_MISS': {'name': 'Items', 'unit': 'miss/sec'},

                    'CONFIG_NOCACHE': {'name': 'Non-Cacheable Items',
                                       'unit': 'requests/sec'},
                    'NONE': {'name': 'Items Not Checked', 'unit': 'sec'},
                    'TCP_CLIENT_REFRESH_MISS': {'name': 'Stale Items Updated',
                                                'unit': 'miss/sec'},
                    'UNCACHEABLE': {'name': 'Cache Errors', 'unit': 'sec'}}

    MEDIA_TYPES = {1: 'Windows Media Streaming',
                   2: 'Flash Media Streaming',
                   3: 'HTTP Large',
                   8: 'HTTP Small'}

    WMS = 1
    FMS = 2
    HTTP_LARGE = 3
    HTTP_SMALL = 8

    def add_overview_metrics(self):
        bandwidth = self.fetch_bandwidth_values()
        for media_type in [self.FMS, self.HTTP_LARGE, self.HTTP_SMALL]:
            if bandwidth[media_type]:
                self.add_gauge_value('%s/Bandwidth' %
                                     self.MEDIA_TYPES[media_type],
                                     'bits/sec',
                                     bandwidth[media_type].get('Result', 0))

    def add_cache_metrics(self):
        cache_values = self.fetch_cache_values()
        for media_type in [self.HTTP_LARGE, self.HTTP_SMALL]:
            for cache_value in cache_values[media_type]:
                field = self.CACHE_FIELDS[cache_value['CacheStatus']]
                self.add_gauge_value('%s/Cache/%s' %
                                     (self.MEDIA_TYPES[media_type],
                                      field['name']),
                                     field['unit'],
                                     cache_value['Connections'])

    def add_connection_metrics(self):
        connection = self.fetch_connection_values()
        for media_type in [self.WMS, self.FMS,
                           self.HTTP_LARGE, self.HTTP_SMALL]:
            if connection[media_type]:
                self.add_gauge_value('%s/Connections' %
                                     self.MEDIA_TYPES[media_type],
                                     'connections',
                                     connection[media_type].get('Result', 0))

    def add_statuscode_metrics(self):
        cache_values = self.fetch_statuscode_values()
        for media_type in [self.HTTP_LARGE, self.HTTP_SMALL]:
            for value in cache_values[media_type]:
                self.add_gauge_value('%s/ResponseCodes/%s' %
                                     (self.MEDIA_TYPES[media_type],
                                      value['StatusCode']),
                                     'responses/sec',
                                     value['Connections'])

    @property
    def edgecast_base_url(self):
        return 'http://api.edgecast.com/v2/{API}/customers/%(account)s' % \
               self.config

    def fetch_bandwidth_values(self):
        values = dict()
        for key in [self.FMS, self.HTTP_LARGE, self.HTTP_SMALL]:
            values[key] = self.fetch_remote_resource('realtimestats',
                                                     'media/%i/bandwidth' %
                                                     key)
        return values

    def fetch_cache_values(self):
        values = dict()
        for key in [self.HTTP_LARGE, self.HTTP_SMALL]:
            values[key] = self.fetch_remote_resource('realtimestats',
                                                     'media/%i/cachestatus' %
                                                     key)
        return values

    def fetch_connection_values(self):
        values = dict()
        for key in [self.WMS, self.FMS, self.HTTP_LARGE, self.HTTP_SMALL]:
            values[key] = self.fetch_remote_resource('realtimestats',
                                                     'media/%i/connections' %
                                                     key)
        return values

    def fetch_statuscode_values(self):
        values = dict()
        for key in [self.HTTP_LARGE, self.HTTP_SMALL]:
            values[key] = self.fetch_remote_resource('realtimestats',
                                                     'media/%i/statuscode' %
                                                     key)
        return values

    def fetch_remote_resource(self, api, path):
        url = ('%s/%s' % (self.edgecast_base_url, path)).replace('{API}', api)
        LOGGER.info('Fetching remote resource from %s', url)
        response = requests.get(url, headers=self.request_headers)
        if response.status_code != 200:
            LOGGER.error('Unexpected response (%s): %s',
                         response.status_code, response.content)
            return dict()
        return response.json()

    def poll(self):
        start_time = time.time()
        self.derive = dict()
        self.gauge = dict()
        self.rate = dict()
        self.add_overview_metrics()
        self.add_cache_metrics()
        self.add_connection_metrics()
        self.add_statuscode_metrics()
        LOGGER.info('Polling complete in %.2f seconds',
                    time.time() - start_time)

    @property
    def request_headers(self):
        return {'Accept': 'application/json',
                'Authorization': 'TOK:%s' % self.config['token'],
                'Content-Type': 'application/json'}
