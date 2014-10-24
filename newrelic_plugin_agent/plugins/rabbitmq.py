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
    DEFAULT_HOST = 'localhost'
    DEFAULT_PORT = 80
    DEFAULT_API_PATH = '/api'

    DUMMY_STATS = {'ack': 0,
                   'deliver': 0,
                   'deliver_no_ack': 0,
                   'get': 0,
                   'get_no_ack': 0,
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
            self.add_gauge_value('%s/Channels/Open' % base_name,
                                 'channels', count)
            self.add_gauge_value('%s/Erlang Processes' % base_name, 'processes',
                                 node.get('proc_used', 0))
            self.add_gauge_value('%s/File Descriptors' % base_name, 'fds',
                                 node.get('fd_used', 0))
            self.add_gauge_value('%s/Memory' % base_name, 'bytes',
                                 node.get('mem_used', 0))
            self.add_gauge_value('%s/Sockets' % base_name, 'sockets',
                                 node.get('sockets_used', 0))

        # Summary stats
        self.add_gauge_value('Summary/Channels', 'channels', channels)
        self.add_gauge_value('Summary/Consumers', 'consumers', self.consumers)

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

        self.add_gauge_value('Node/%s/Channels/Blocked' % node, 'channels',
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
            name = key
            if key == 'ack':
                name = 'Acknowledged'
            elif key == 'deliver':
                name = 'Delivered'
            elif key == 'deliver_get':
                name = 'Delivered (Total)'
            elif key == 'deliver_no_ack':
                name = 'Delivered No-Ack'
            elif key == 'get':
                name = 'Got'
            elif key == 'get_no_ack':
                name = 'Got No-Ack'
            elif key == 'publish':
                name = 'Published'
            elif key == 'redeliver':
                name = 'Redelivered'
            self.add_derive_value('%s/%s' % (base_name, name),
                                  'messages',
                                  total[key])

        keys = ['messages_ready', 'messages_unacknowledged']
        count, total, min_val, max_val, values = self.initialize_counters(keys)
        for queue in queue_data:
            if queue['node'].split('@')[-1] == node:
                for key in keys:
                    total[key] += queue.get(key, 0)

        self.add_gauge_value('%s Available' % base_name, 'messages',
                             total['messages_ready'])
        self.add_gauge_value('%s Unacknowledged' % base_name,
                             'messages',
                             total['messages_unacknowledged'])

    def add_node_queue_datapoints(self, node, queue_data):
        """Add datapoints for a node, creating summary values for top-level
        queue consumer counts and message counts.

        :param str node: The node name
        :param list queue_data: The full stack of queue metrics

        """
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

                # Inventing a new key here, so it's a manual override
                key = 'idle_consumers'
                count[key] += count['consumers']
                idle_count = total['consumers'] - total['active_consumers']
                total[key] += idle_count
                values[key].append(idle_count)

        base_name = 'Node/%s/Consumers' % node
        self.add_gauge_value('%s/Count' % base_name, 'consumers',
                             total['consumers'],
                             None,
                             None,
                             count['consumers'])

        self.consumers += total['consumers']

        self.add_gauge_value('%s/Active' % base_name, 'consumers',
                             total['active_consumers'],
                             None,
                             None,
                             count['active_consumers'])

        base_name = 'Node/%s/Consumers' % node
        self.add_gauge_value('%s/Idle' % base_name, 'consumers',
                             total['idle_consumers'],
                             None,
                             None,
                             count['idle_consumers'])

    def track_vhost_queue(self, vhost_name, queue_name):
        """ Checks whether the data for a vhost queue should be tracked or not
        The check is based on the user configs, no configs means track everything
        :param str vhost_name: the virtual host name
        :param str queue_name: the queue name
        """
        TRACK_EVERYTHING = dict()
        tracked_vhosts = self.config.get('vhosts', TRACK_EVERYTHING)
        vhost_settings = tracked_vhosts.get(vhost_name) or {}
        vhost_queues = vhost_settings.get('queues', [])
        if tracked_vhosts is TRACK_EVERYTHING:
            return True
        if vhost_name in tracked_vhosts and vhost_queues == []:
            return True
        return queue_name in vhost_queues

    def add_queue_datapoints(self, queue_data):
        """Add per-queue datapoints to the processing stack.

        :param list queue_data: The raw queue data list

        """
        count = 0
        available, consumers, deliver, publish, redeliver, unacked = \
            0, 0, 0, 0, 0, 0
        for count, queue in enumerate(queue_data):
            if queue['name'][0:7] == 'amq.gen':
                LOGGER.debug('Skipping auto-named queue: %s', queue['name'])
                continue

            message_stats = queue.get('message_stats', dict())
            if not message_stats:
                message_stats = self.DUMMY_STATS

            vhost = 'Default' if queue['vhost'] == '/' else queue['vhost']
            base_name = 'Queue/%s/%s' % (vhost, queue['name'])

            if not self.track_vhost_queue(vhost, queue['name']):
                continue

            self.add_gauge_value('%s/Consumers' % base_name, 'consumers',
                                 queue.get('consumers', 0))

            base_name = 'Queue/%s/%s/Messages' % (vhost, queue['name'])
            self.add_derive_value('%s/Acknowledged' % base_name, 'messages',
                                  message_stats.get('ack', 0))
            self.add_derive_value('%s/Delivered (All)' % base_name, 'messages',
                                  message_stats.get('deliver_get', 0))
            self.add_derive_value('%s/Delivered' % base_name, 'messages',
                                  message_stats.get('deliver', 0))
            self.add_derive_value('%s/Delivered No-Ack' % base_name, 'messages',
                                  message_stats.get('deliver_no_ack', 0))
            self.add_derive_value('%s/Get' % base_name, 'messages',
                                  message_stats.get('get', 0))
            self.add_derive_value('%s/Get No-Ack' % base_name, 'messages',
                                  message_stats.get('get_no_ack', 0))
            self.add_derive_value('%s/Published' % base_name, 'messages',
                                  message_stats.get('publish', 0))
            self.add_derive_value('%s/Redelivered' % base_name, 'messages',
                                  message_stats.get('redeliver', 0))

            self.add_gauge_value('%s Available' % base_name, 'messages',
                                 queue.get('messages_ready', 0))
            self.add_gauge_value('%s Unacknowledged' % base_name, 'messages',
                                 queue.get('messages_unacknowledged', 0))

            available += queue.get('messages_ready', 0)
            deliver += message_stats.get('deliver_get', 0)
            publish += message_stats.get('publish', 0)
            redeliver += message_stats.get('redeliver', 0)
            unacked += queue.get('messages_unacknowledged', 0)

        # Summary stats
        self.add_derive_value('Summary/Messages/Delivered', 'messages',
                              deliver, count=count)
        self.add_derive_value('Summary/Messages/Published', 'messages',
                              publish, count=count)
        self.add_derive_value('Summary/Messages/Redelivered', 'messages',
                              redeliver, count=count)

        self.add_gauge_value('Summary/Messages Available', 'messages',
                             available, count=count)
        self.add_gauge_value('Summary/Messages Unacknowledged', 'messages',
                             unacked, count=count)

    def http_get(self, url, params=None):
        """Make a HTTP request for the URL.

        :param str url: The URL to request
        :param dict params: Get query string parameters

        """
        kwargs = {'url': url,
                  'auth': (self.config.get('username', self.DEFAULT_USER),
                           self.config.get('password', self.DEFAULT_PASSWORD)),
                  'verify': self.config.get('verify_ssl_cert', True)}
        if params:
            kwargs['params'] = params

        try:
            return self.requests_session.get(**kwargs)
        except requests.ConnectionError as error:
            LOGGER.error('Error fetching data from %s: %s', url, error)
            return None

    def fetch_data(self, data_type, columns=None):
        """Fetch the data from the RabbitMQ server for the specified data type

        :param str data_type: The type of data to query
        :param list columns: Ask for specific columns
        :rtype: list

        """
        url = '%s/%s' % (self.rabbitmq_base_url, data_type)
        params = {'columns': ','.join(columns)} if columns else {}
        response = self.http_get(url, params)
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

        self.requests_session = requests.Session()

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
        port = self.config.get('port', self.DEFAULT_PORT)
        secure = self.config.get('secure', False)
        host = self.config.get('host', self.DEFAULT_HOST)
        api_path = self.config.get('api_path', self.DEFAULT_API_PATH)
        scheme = 'https' if secure else 'http'

        return '{scheme}://{host}:{port}{api_path}'.format(
            scheme=scheme, host=host, port=port, api_path=api_path)
