"""
Base Plugin Classes

"""
import csv
import logging
from os import path
import requests
import socket
import tempfile
import time
import urlparse

LOGGER = logging.getLogger(__name__)


class Plugin(object):

    GUID = 'com.meetme.newrelic_plugin_agent'
    MAX_VAL = 2147483647

    def __init__(self, config, poll_interval, last_interval_values=None):
        self.config = config
        LOGGER.debug('%s config: %r', self.__class__.__name__, self.config)
        self.poll_interval = poll_interval
        self.poll_start_time = 0

        self.derive_values = dict()
        self.derive_last_interval = last_interval_values or dict()
        self.gauge_values = dict()

    def add_datapoints(self, data):
        """Extend this method to process the data points retrieved during the
        poll process.

        :param mixed data: The data received during the poll process

        """
        raise NotImplementedError

    def add_derive_value(self, metric_name, units, value, count=None):
        """Add a value that will derive the current value from the difference
        between the last interval value and the current value.

        If this is the first time a stat is being added, it will report a 0
        value until the next poll interval and it is able to calculate the
        derivative value.

        :param str metric_name: The name of the metric
        :param str units: The unit type
        :param int value: The value to add
        :param int count: The number of items the timing is for

        """
        if value is None:
            value = 0
        metric = self.metric_name(metric_name, units)
        if metric not in self.derive_last_interval.keys():
            LOGGER.debug('Bypassing initial %s value for first run', metric)
            self.derive_values[metric] = self.metric_payload(0, count=0)
        else:
            cval = value - self.derive_last_interval[metric]
            self.derive_values[metric] = self.metric_payload(cval, count=count)
            LOGGER.debug('%s: Last: %r, Current: %r, Reporting: %r',
                         metric, self.derive_last_interval[metric], value,
                         self.derive_values[metric])
        self.derive_last_interval[metric] = value

    def add_derive_timing_value(self, metric_name, units, count, total_value,
                                last_value=None):
        """For timing based metrics that have a count of objects for the timing
        and an optional last value.

        :param str metric_name: The name of the metric
        :param str units: The unit type
        :param int count: The number of items the timing is for
        :param int total_value: The timing value
        :param int last_value: The last value

        """
        if last_value is None:
            return self.add_derive_value(metric_name, units,
                                         total_value, count)
        self.add_derive_value('%s/Total' % metric_name,
                              units, total_value, count)
        self.add_derive_value('%s/Last' % metric_name,
                              units, last_value, count)

    def add_gauge_value(self, metric_name, units, value,
                        min_val=None, max_val=None, count=None,
                        sum_of_squares=None):
        """Add a value that is not a rolling counter but rather an absolute
        gauge

        :param str metric_name: The name of the metric
        :param str units: The unit type
        :param int value: The value to add
        :param float value: The sum of squares for the values

        """
        metric = self.metric_name(metric_name, units)
        self.gauge_values[metric] = self.metric_payload(value,
                                                        min_val,
                                                        max_val,
                                                        count,
                                                        sum_of_squares)
        LOGGER.debug('%s: %r', metric_name, self.gauge_values[metric])

    def component_data(self):
        """Create the component section of the NewRelic Platform data payload
        message.

        :rtype: dict

        """
        metrics = dict()
        metrics.update(self.derive_values.items())
        metrics.update(self.gauge_values.items())
        return {'name': self.name,
                'guid': self.GUID,
                'duration': self.poll_interval,
                'metrics': metrics}

    def error_message(self):
        """Output an error message when stats collection fails"""
        LOGGER.error('Error collecting stats data from %s. Please check '
                     'configuration and sure it conforms with YAML '
                     'syntax', self.__class__.__name__)

    def finish(self):
        """Note the end of the stat collection run and let the user know of any
        errors.

        """
        if not self.derive_values and not self.gauge_values:
            self.error_message()
        else:
            LOGGER.info('%s poll successful, completed in %.2f seconds',
                        self.__class__.__name__,
                        time.time() - self.poll_start_time)

    def initialize(self):
        """Empty stats collection dictionaries for the polling interval"""
        self.poll_start_time = time.time()
        self.derive_values = dict()
        self.gauge_values = dict()

    def initialize_counters(self, keys):
        """Create a new set of counters for the given key list

        :param list keys: Keys to initialize in the counters
        :rtype: tuple

        """
        count, total, min_val, max_val, values = (dict(), dict(), dict(),
                                                  dict(), dict())
        for key in keys:
            (count[key], total[key], min_val[key],
             max_val[key], values[key]) = 0, 0, self.MAX_VAL, 0, list()
        return count, total, min_val, max_val, values

    def metric_name(self, metric, units):
        """Return the metric name in the format for the NewRelic platform

        :param str metric: The name of th metric
        :param str units: The unit name

        """
        if not units:
            return 'Component/%s' % metric
        return 'Component/%s[%s]' % (metric, units)

    def metric_payload(self, value, min_value=None, max_value=None, count=None,
                       squares=None):
        """Return the metric in the standard payload format for the NewRelic
        agent.

        :rtype: dict

        """
        if isinstance(value, basestring):
            value = 0

        sum_of_squares = int(squares or (value * value))
        if sum_of_squares > self.MAX_VAL:
            sum_of_squares = 0

        return {'min': min_value,
                'max': max_value,
                'total': value,
                'count': count or 1,
                'sum_of_squares': sum_of_squares}

    @property
    def name(self):
        """Return the name of the component

        :rtype: str

        """
        return self.config.get('name', socket.gethostname().split('.')[0])

    def poll(self):
        """Poll the server returning the results in the expected component
        format.

        """
        raise NotImplementedError

    def sum_of_squares(self, values):
        """Return the sum_of_squares for the given values

        :param list values: The values list
        :rtype: float

        """
        value_sum = sum(values)
        if not value_sum:
            return 0
        squares = list()
        for value in values:
            squares.append(value * value)
        return sum(squares) - float(value_sum * value_sum) / len(values)

    def values(self):
        """Return the poll results

        :rtype: dict

        """
        return self.component_data()


class SocketStatsPlugin(Plugin):
    """Connect to a socket and collect stats data"""
    DEFAULT_HOST = 'localhost'
    DEFAULT_PORT = 0
    SOCKET_RECV_MAX = 10485760

    def connect(self):
        """Top level interface to create a socket and connect it to the
        socket.

        :rtype: socket

        """
        try:
            connection = self.socket_connect()
        except socket.error as error:
            LOGGER.error('Error connecting to %s: %s',
                         self.__class__.__name__, error)
        else:
            return connection

    def fetch_data(self, connection, read_till_empty=False):
        """Read the data from the socket

        :param  socket connection: The connection

        """
        LOGGER.debug('Fetching data')
        received = connection.recv(self.SOCKET_RECV_MAX)
        while read_till_empty:
            chunk = connection.recv(self.SOCKET_RECV_MAX)
            if chunk:
                received += chunk
            else:
                break
        return received

    def poll(self):
        """This method is called after every sleep interval. If the intention
        is to use an IOLoop instead of sleep interval based daemon, override
        the run method.

        """
        LOGGER.info('Polling %s', self.__class__.__name__)
        self.initialize()

        # Fetch the data from the remote socket
        connection = self.connect()
        if not connection:
            LOGGER.error('%s could not connect, skipping poll interval',
                         self.__class__.__name__)
            return

        data = self.fetch_data(connection)
        connection.close()

        if data:
            self.add_datapoints(data)
            self.finish()
        else:
            self.error_message()

    def socket_connect(self):
        """Low level interface to create a socket and connect to it.

        :rtype: socket

        """
        if 'path' in self.config:
            if path.exists(self.config['path']):
                LOGGER.debug('Connecting to UNIX domain socket: %s',
                             self.config['path'])
                connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                connection.connect(self.config['path'])
            else:
                LOGGER.error('UNIX domain socket path does not exist: %s',
                             self.config['path'])
                return None
        else:
            remote_host = (self.config.get('host', self.DEFAULT_HOST),
                           self.config.get('port', self.DEFAULT_PORT))
            LOGGER.debug('Connecting to %r', remote_host)
            connection = socket.socket()
            connection.connect(remote_host)
        return connection


class HTTPStatsPlugin(Plugin):
    """Extend the Plugin class overriding poll for targets that provide data
    via HTTP protocol.

    """
    DEFAULT_PATH = '/'
    DEFAULT_QUERY = None

    def fetch_data(self):
        """Fetch the data from the stats URL

        :rtype: str

        """
        data = self.http_get()
        return data.content if data else ''

    def http_get(self):
        """Fetch the data from the stats URL

        :rtype: requests.models.Response

        """
        LOGGER.debug('Polling %s Stats at %s',
                     self.__class__.__name__, self.stats_url)
        try:
            response = requests.get(**self.request_kwargs)
        except requests.ConnectionError as error:
            LOGGER.error('Error polling stats: %s', error)
            return ''

        if response.status_code >= 300:
            LOGGER.error('Error response from %s (%s): %s', self.stats_url,
                         response.status_code, response.content)
            return None
        return response

    def poll(self):
        """Poll HTTP server for stats data"""
        self.initialize()
        data = self.fetch_data()
        if data:
            self.add_datapoints(data)
        self.finish()

    @property
    def stats_url(self):
        """Return the configured URL in a uniform way for all HTTP based data
        sources.

        :rtype: str

        """
        netloc = self.config.get('host', 'localhost')
        if self.config.get('port'):
            netloc += ':%s' % self.config['port']

        return urlparse.urlunparse((self.config.get('scheme', 'http'),
                                    netloc,
                                    self.config.get('path', self.DEFAULT_PATH),
                                    None,
                                    self.config.get('query',
                                                    self.DEFAULT_QUERY),
                                    None))

    @property
    def request_kwargs(self):
        """Return kwargs for a HTTP request.

        :rtype: dict

        """
        kwargs = {'url': self.stats_url}
        if self.config.get('scheme') == 'https':
            kwargs['verify'] = self.config.get('verify_ssl_cert', False)

        if 'username' in self.config and 'password' in self.config:
            kwargs['auth'] = (self.config['username'], self.config['password'])

        LOGGER.debug('Request kwargs: %r', kwargs)
        return kwargs


class CSVStatsPlugin(HTTPStatsPlugin):
    """Extend the Plugin overriding poll for targets that provide JSON output
    for stats collection

    """
    def fetch_data(self):
        """Fetch the data from the stats URL

        :rtype: dict

        """
        data = super(CSVStatsPlugin, self).fetch_data()
        if not data:
            return dict()
        temp = tempfile.TemporaryFile()
        temp.write(data)
        temp.seek(0)
        reader = csv.DictReader(temp)
        data = list()
        for row in reader:
            data.append(row)
        temp.close()
        return data

    def poll(self):
        """Poll HTTP JSON endpoint for stats data"""
        self.initialize()
        data = self.fetch_data()
        if data:
            self.add_datapoints(data)
        self.finish()


class JSONStatsPlugin(HTTPStatsPlugin):
    """Extend the Plugin overriding poll for targets that provide JSON output
    for stats collection

    """
    def fetch_data(self):
        """Fetch the data from the stats URL

        :rtype: dict

        """
        data = self.http_get()
        try:
            return data.json() if data else {}
        except Exception as error:
            LOGGER.error('JSON decoding error: %r', error)
        return {}

    def poll(self):
        """Poll HTTP JSON endpoint for stats data"""
        self.initialize()
        data = self.fetch_data()
        if data:
            self.add_datapoints(data)
        self.finish()
