"""
Elastic Search

"""
import logging
import requests

from newrelic_plugin_agent.plugins import base

LOGGER = logging.getLogger(__name__)


class ElasticSearch(base.JSONStatsPlugin):

    DERIVE_PARTIAL = ['Opens', 'Errs', 'Segs']
    DERIVE_MATCH = ['total', 'completed', 'rejected',
                    'total_opened', 'collection_count']
    GAUGE_MATCH = ['Current']

    DEFAULT_HOST = 'localhost'
    DEFAULT_PATH = '/_nodes/stats?all'
    DEFAULT_PORT = 9200
    GUID = 'com.meetme.newrelic_elasticsearch_node_agent'

    STATUS_CODE = {'green': 0, 'yellow': 1, 'red': 2}

    def add_datapoints(self, stats):
        """Add all of the datapoints for the Elasticsearch poll

        :param dict stats: The stats to process for the values

        """
        totals = dict()
        for node in stats.get('nodes'):
            for key in stats['nodes'][node].keys():
                if isinstance(stats['nodes'][node][key], dict):
                    if key not in totals:
                        totals[key] = dict()
                    self.process_tree(totals[key],
                                      stats['nodes'][node][key])

        self.add_index_datapoints(totals)
        self.add_network_datapoints(totals)
        self.add_cluster_stats()

    def add_cluster_stats(self):
        """Add stats that go under Component/Cluster"""
        url = self.stats_url.replace(self.DEFAULT_PATH, '/_cluster/health')
        response = self.http_get(url)
        if response.status_code == 200:
            data = response.json()
            self.add_gauge_value('Cluster/Status', 'level',
                                 self.STATUS_CODE[data.get('status', 'red')])
            self.add_gauge_value('Cluster/Nodes', 'nodes',
                                 data.get('number_of_nodes', 0))
            self.add_gauge_value('Cluster/Data Nodes', 'nodes',
                                 data.get('number_of_data_nodes', 0))
            self.add_gauge_value('Cluster/Shards/Active', 'shards',
                                 data.get('active_shards', 0))
            self.add_gauge_value('Cluster/Shards/Initializing', 'shards',
                                 data.get('initializing_shards', 0))
            self.add_gauge_value('Cluster/Shards/Primary', 'shards',
                                 data.get('active_primary_shards', 0))
            self.add_gauge_value('Cluster/Shards/Relocating', 'shards',
                                 data.get('relocating_shards', 0))
            self.add_gauge_value('Cluster/Shards/Unassigned', 'shards',
                                 data.get('unassigned_shards', 0))
        else:
            LOGGER.error('Error collecting cluster stats (%s): %s',
                         response.status_code, response.content)

    def add_index_datapoints(self, stats):
        """Add the data points for Component/Indices

        :param dict stats: The stats to process for the values

        """
        indices = stats.get('indices', dict())

        docs = indices.get('docs', dict())
        self.add_gauge_value('Indices/Documents/Count', 'docs',
                             docs.get('count', 0))
        self.add_derive_value('Indices/Documents/Added', 'docs',
                              docs.get('count', 0))
        self.add_derive_value('Indices/Documents/Deleted', 'docs',
                              docs.get('deleted', 0))

        store = indices.get('store', dict())
        self.add_gauge_value('Indices/Storage', 'bytes',
                             store.get('size_in_bytes', 0))
        self.add_derive_value('Indices/Storage Throttled', 'ms',
                              store.get('throttle_time_in_millis', 0))

        indexing = indices.get('indexing', dict())
        self.add_derive_value('Indices/Indexing', 'ms',
                              indexing.get('index_time_in_millis', 0))
        self.add_derive_value('Indices/Indexing', 'count',
                              indexing.get('index_total', 0))
        self.add_derive_value('Indices/Index Deletes', 'ms',
                              indexing.get('delete_time_in_millis', 0))
        self.add_derive_value('Indices/Index Deletes', 'count',
                              indexing.get('delete_total', 0))

        get_stats = indices.get('get', dict())
        self.add_derive_value('Indices/Get', 'count',
                             get_stats.get('total', 0))
        self.add_derive_value('Indices/Get', 'ms',
                              get_stats.get('time_in_millis', 0))
        self.add_derive_value('Indices/Get Hits', 'count',
                              get_stats.get('exists_total', 0))
        self.add_derive_value('Indices/Get Hits', 'ms',
                              get_stats.get('exists_time_in_millis', 0))
        self.add_derive_value('Indices/Get Misses', 'count',
                              get_stats.get('missing_total', 0))
        self.add_derive_value('Indices/Get Misses', 'ms',
                              get_stats.get('missing_time_in_millis', 0))

        search = indices.get('search', dict())
        self.add_gauge_value('Indices/Open Search Contexts', 'count',
                             search.get('open_contexts', 0))
        self.add_derive_value('Indices/Search Query', 'count',
                             search.get('query_total', 0))
        self.add_derive_value('Indices/Search Query', 'ms',
                              search.get('query_time_in_millis', 0))

        self.add_derive_value('Indices/Search Fetch', 'count',
                             search.get('fetch_total', 0))
        self.add_derive_value('Indices/Search Fetch', 'ms',
                              search.get('fetch_time_in_millis', 0))

        merge_stats = indices.get('merge', dict())
        self.add_derive_value('Indices/Merge', 'count',
                              merge_stats.get('total', 0))
        self.add_derive_value('Indices/Merge', 'ms',
                              merge_stats.get('total_time_in_millis', 0))

        flush_stats = indices.get('flush', dict())
        self.add_gauge_value('Indices/Flush', 'count',
                             flush_stats.get('total', 0))
        self.add_derive_value('Indices/Flush', 'ms',
                              flush_stats.get('total_time_in_millis', 0))

    def add_network_datapoints(self, stats):
        """Add the data points for Component/Network

        :param dict stats: The stats to process for the values

        """
        transport = stats.get('transport', dict())
        self.add_derive_value('Network/Traffic/Received', 'bytes',
                              transport.get('rx_size_in_bytes', 0))
        self.add_derive_value('Network/Traffic/Sent', 'bytes',
                              transport.get('tx_size_in_bytes', 0))

        network = stats.get('network', dict())
        self.add_derive_value('Network/Connections/Active', 'conn',
                              network.get('active_opens', 0))
        self.add_derive_value('Network/Connections/Passive', 'conn',
                              network.get('passive_opens', 0))
        self.add_derive_value('Network/Connections/Reset', 'conn',
                              network.get('estab_resets', 0))
        self.add_derive_value('Network/Connections/Failures', 'conn',
                              network.get('attempt_fails', 0))

        self.add_derive_value('Network/HTTP Connections', 'conn',
                              stats.get('http', dict()).get('total_opened', 0))

        self.add_derive_value('Network/Segments/In', 'seg',
                              network.get('in_seg', 0))
        self.add_derive_value('Network/Segments/In', 'errors',
                              network.get('in_errs', 0))
        self.add_derive_value('Network/Segments/Out', 'seg',
                              network.get('out_seg', 0))
        self.add_derive_value('Network/Segments/Retransmitted', 'seg',
                              network.get('retrans_segs', 0))

    def process_tree(self, tree, values):
        """Recursively combine all node stats into a single top-level value

        :param dict tree: The output values
        :param dict values: The input values

        """
        for key in values:
            if key == 'timestamp':
                continue
            if isinstance(values[key], dict):
                if key not in tree:
                    tree[key] = dict()
                self.process_tree(tree[key], values[key])
            elif isinstance(values[key], int):
                if key not in tree:
                    tree[key] = 0
                tree[key] += values[key]
