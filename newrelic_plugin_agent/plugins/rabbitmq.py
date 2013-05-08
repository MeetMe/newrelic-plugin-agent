"""
rabbitmq

"""
import logging
import requests
import time

from newrelic_plugin_agent.plugins import base

LOGGER = logging.getLogger(__name__)


class RabbitMQ(base.Plugin):

    GUID = 'com.meetme.newrelic_rabbitmq_agent'

    DEFAULT_USER = 'guest'
    DEFAULT_PASSWORD = 'guest'

    DELIVER_KEYS = ['deliver', 'deliver_get', 'deliver_no_ack']

    DUMMY_STATS = {'ack': 0,
                   'deliver': 0,
                   'deliver_get': 0,
                   'deliver_no_ack': 0,
                   'publish': 0,
                   'redeliver': 0}

    def add_node_datapoints(self, node_data, queue_data, channel_data):
        """Add all of the data points for a node

        :param list node_data: all of the nodes
        :param list queue_data: all of the queues
        :param list channel_data: all of the channels

        """
        channels = 0
        for node in node_data:
            name = node['name'].split('@')[-1]
            self.add_node_channel_datapoints(name, channel_data)
            self.add_node_message_datapoints(name, queue_data, channel_data)
            self.add_node_queue_datapoints(name, queue_data)

            count = 0
            for channel in channel_data:
                if channel['node'].split('@')[-1] == name:
                    count += 1
            channels += count

            base_name = 'Node/%s' % name
            self.add_gauge_value('%s/Channels/Count' % base_name,
                                 'Channels', count)
            self.add_gauge_value('%s/Erlang Processes' % base_name,
                                 'Erlang Processes',
                                 node.get('proc_used', 0))
            self.add_gauge_value('%s/File Descriptors' % base_name,
                                 'File Descriptors',
                                 node.get('fd_used', 0))
            self.add_gauge_value('%s/Memory' % base_name, 'mb',
                                 (node.get('mem_used', 0) / 1024) / 1024)
            self.add_gauge_value('%s/Sockets' % base_name, 'Sockets',
                                 node.get('sockets_used', 0))

        # Summary stats
        self.add_gauge_value('Summary/Channels', 'Channels', channels)
        self.add_gauge_value('Summary/Consumers', 'Consumers', self.consumers)

    def add_node_channel_datapoints(self, node, channel_data):
        """Add datapoints for a node, creating summary values for top-level
        queue consumer counts and message counts.

        :param str node: The node name
        :param list channel_data: The full stack of queue metrics

        """
        channel_flow_blocked = 0
        for channel in channel_data:
            if channel['node'].split('@')[-1] == node:
                if channel.get('client_flow_blocked'):
                    channel_flow_blocked += 1

        self.add_gauge_value('Node/%s/Channels/Blocked' % node, 'Channels',
                             channel_flow_blocked)

    def add_node_message_datapoints(self, node, queue_data, channel_data):
        """Add message stats for the node

        :param str node: The node name
        :param list queue_data: all of the queues
        :param list channel_data: all of the channels

        """
        base_name = 'Node/%s/Messages' % node

        # Top level message stats
        keys = self.DUMMY_STATS.keys()
        count, total, min_val, max_val, values = self.initialize_counters(keys)
        for channel in channel_data:
            if channel['node'].split('@')[-1] == node:
                for key in keys:
                    total[key] += channel.get(key, 0)
        for key in keys:
            name = key.split('_')[-1].title()
            self.add_derive_value('%s/%s' % (base_name, name),
                                  'Messages',
                                  total[key])

        # Per-Channel message Rates
        count, total, min_val, max_val, values = self.initialize_counters(keys)
        message_stats = list()
        for channel in channel_data:
            if channel['node'].split('@')[-1] == node:
                stats = channel.get('message_stats')
                if stats:
                    message_stats.append(stats)

        for stat_block in message_stats:
            for key in keys:
                total[key] += stat_block.get(key, 0)

        for key in keys:
            if key != 'deliver_no_ack':
                temp = key.split('_')[-1].title()
                name = '%sed' % temp if temp != 'Get' else temp
            else:
                name = 'Delivered NoAck'
            if name == 'Acked':
                name = 'Acknowledged'
            self.add_derive_value('%s/%s' % (base_name, name),
                                  'Messages',
                                  total[key])

        keys = ['messages_ready', 'messages_unacknowledged']
        count, total, min_val, max_val, values = self.initialize_counters(keys)
        for queue in queue_data:
            if queue['node'].split('@')[-1] == node:
                for key in keys:
                    total[key] += queue.get(key, 0)

        self.add_gauge_value('%s/Available' % base_name, 'Messages',
                             total['messages_ready'])
        self.add_gauge_value('%s/Pending Acknowledgements' % base_name,
                             'Messages',
                             total['messages_unacknowledged'])

    def add_node_queue_datapoints(self, node, queue_data):
        """Add datapoints for a node, creating summary values for top-level
        queue consumer counts and message counts.

        :param str node: The node name
        :param list queue_data: The full stack of queue metrics

        """
        consumers = 0
        keys = ['consumers', 'active_consumers', 'idle_consumers']
        count, total, min_val, max_val, values = self.initialize_counters(keys)
        del keys[2]
        for queue in queue_data:
            if queue['node'].split('@')[-1] == node:
                for key in keys:
                    count[key] += 1
                    value = queue.get(key, 0)
                    total[key] += value
                    values[key].append(value)
                    if value < min_val[key]:
                        min_val[key] = value
                    if value > max_val[key]:
                        max_val[key] = value

                # Inventing a new key here, so it's a manual override
                key = 'idle_consumers'
                count[key] += count['consumers']
                idle_count = total['consumers'] - total['active_consumers']
                total[key] += idle_count
                values[key].append(idle_count)
                if idle_count < min_val[key]:
                    min_val[key] = idle_count
                if idle_count > max_val[key]:
                    max_val[key] = idle_count

        base_name = 'Node/%s/Consumers' % node
        self.add_gauge_value('%s/Count' % base_name, 'Consumers',
                             total['consumers'],
                             min_val['consumers'],
                             max_val['consumers'],
                             count['consumers'],
                             self.sum_of_squares(values['consumers']))

        self.consumers += total['consumers']

        self.add_gauge_value('%s/Active' % base_name, 'Consumers',
                             total['active_consumers'],
                             min_val['active_consumers'],
                             max_val['active_consumers'],
                             count['active_consumers'],
                             self.sum_of_squares(values['active_consumers']))

        base_name = 'Node/%s/Consumers' % node
        self.add_gauge_value('%s/Idle' % base_name, 'Consumers',
                             total['idle_consumers'],
                             min_val['idle_consumers'],
                             max_val['idle_consumers'],
                             count['idle_consumers'],
                             self.sum_of_squares(values['idle_consumers']))

    def add_queue_datapoints(self, queue_data):
        """Add per-queue datapoints to the processing stack.

        :param list queue_data: The raw queue data list

        """
        available, deliver, publish = 0, 0, 0
        for queue in queue_data:
            message_stats = queue.get('message_stats', list())
            if not message_stats:
                message_stats = self.DUMMY_STATS

            vhost = 'Default' if queue['vhost'] == '/' else queue['vhost']
            base_name = 'Queue/%s/%s/Messages' % (vhost, queue['name'])
            self.add_derive_value('%s/Acknowledged' % base_name, 'Messages',
                                  queue.get('ack', 0))
            self.add_derive_value('%s/Available' % base_name, 'Messages',
                                  message_stats.get('messages_ready', 0))
            self.add_derive_value('%s/Delivered' % base_name, 'Messages',
                                  self.delivered_messages(message_stats))
            self.add_derive_value('%s/Published' % base_name, 'Messages',
                                  message_stats.get('publish', 0))
            self.add_derive_value('%s/Redelivered' % base_name, 'Messages',
                                  message_stats.get('ack', 0))
            self.add_derive_value('%s/Unacknowledged' % base_name, 'Messages',
                                  queue.get('ack', 0))
            available += message_stats.get('messages_ready', 0)
            deliver += message_stats.get('deliver', 0)
            publish += message_stats.get('publish', 0)

        # Summary stats
        self.add_derive_value('Summary/Messages/Available', 'Messages',
                              available)
        self.add_derive_value('Summary/Messages/Delivered', 'Messages',
                              deliver)
        self.add_derive_value('Summary/Messages/Published', 'Messages',
                              publish)

    def delivered_messages(self, message_stats):
        """Count the message delivery stats for the given dict and the
        delivery keys combining all.

        :param dict message_stats: The per-queue message stats
        :rtype: int

        """
        count = 0
        for key in self.DELIVER_KEYS:
            count += message_stats.get(key, 0)
        return count

    def http_get(self, url):
        """Make a HTTP request for the URL.

        :param str url: The URL to request

        """
        try:
            return requests.get(url,
                                auth=(self.config.get('username',
                                                      self.DEFAULT_USER),
                                      self.config.get('password',
                                                      self.DEFAULT_PASSWORD)))
        except requests.ConnectionError as error:
            LOGGER.error('Error fetching data from %s: %s', url, error)
            return None

    def fetch_data(self, data_type):
        """Fetch the data from the RabbitMQ server for the specified data type

        :rtype: list

        """
        url = '%s/%s' % (self.rabbitmq_base_url, data_type)
        response = self.http_get(url)
        if not response or response.status_code != 200:
            if response:
                LOGGER.error('Error response from %s (%s): %s', url,
                             response.status_code, response.content)
            return list()

        try:
            return response.json()
        except Exception as error:
            LOGGER.error('JSON decoding error: %r', error)
            return list()

    def fetch_channel_data(self):
        """Return the channel data from the RabbitMQ server

        :rtype: list

        """
        return self.fetch_data('channels')

    def fetch_node_data(self):
        """Return the node data from the RabbitMQ server

        :rtype: list

        """
        return self.fetch_data('nodes')

    def fetch_queue_data(self):
        """Return the queue data from the RabbitMQ server

        :rtype: list

        """
        return self.fetch_data('queues')

    def poll(self):
        """Poll the RabbitMQ server"""
        LOGGER.info('Polling RabbitMQ via %s', self.rabbitmq_base_url)
        start_time = time.time()

        # Initialize the values each iteration
        self.derive = dict()
        self.gauge = dict()
        self.rate = dict()
        self.consumers = 0

        # Fetch the data from RabbitMQ
        channel_data = self.fetch_channel_data()
        node_data = self.fetch_node_data()
        queue_data = self.fetch_queue_data()

        # Create all of the metrics
        self.add_queue_datapoints(queue_data)
        self.add_node_datapoints(node_data, queue_data, channel_data)
        LOGGER.info('Polling complete in %.2f seconds',
                    time.time() - start_time)

    @property
    def rabbitmq_base_url(self):
        """Return the fully composed RabbitMQ base URL

        :rtype: str

        """
        return 'http://%(host)s:%(port)s/api' % self.config
