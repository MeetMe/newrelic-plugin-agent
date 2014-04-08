"""
PHP FPM Support

"""
import logging

from newrelic_plugin_agent.plugins import base

LOGGER = logging.getLogger(__name__)


class FPM(base.JSONStatsPlugin):

    GUID = 'com.meetme.newrelic_php_fpm_agent'

    def add_datapoints(self, stats):
        """Add all of the data points for a fpm-pool

        :param dict stats: Stats from php-fpm for a pool

        """
        self.add_derive_value('Connections/Accepted', 'connections',
                              stats.get('accepted conn', 0))

        self.add_gauge_value('Connections/Pending', 'connections',
                             stats.get('listen queue', 0),
                             max_val=stats.get('max listen queue', 0))

        self.add_gauge_value('Socket Queue', 'connections',
                             stats.get('listen queue len', 0))

        self.add_gauge_value('Processes/Active', 'processes',
                             stats.get('active processes', 0),
                             max_val=stats.get('max processes', 0))

        self.add_gauge_value('Processes/Idle', 'processes',
                             stats.get('idle processes', 0))

        self.add_derive_value('Process Limit Reached', 'processes',
                              stats.get('max children reached', 0))

        self.add_derive_value('Slow Requests', 'requests',
                              stats.get('slow requests', 0))
