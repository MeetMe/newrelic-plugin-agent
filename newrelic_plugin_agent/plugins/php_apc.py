"""
PHP APC Support

"""
import logging
import requests
import time

from newrelic_plugin_agent.plugins import base

LOGGER = logging.getLogger(__name__)

class APC(base.JSONStatsPlugin):

    GUID = 'com.meetme.newrelic_php_apc_agent'

    def add_datapoints(self, stats):
        """Add all of the data points for a node

        :param dict stats: The stats content from APC as a string

        """
        shared_memory = stats.get('shared_memory', dict())
        self.add_gauge_value('Shared Memory/Available', 'Bytes',
                             shared_memory.get('avail_mem', 0))
        self.add_gauge_value('Shared Memory/Segment Size', 'Bytes',
                             shared_memory.get('seg_size', 0))
        self.add_gauge_value('Shared Memory/Segment Count', '',
                             shared_memory.get('num_seg', 0))

        user_stats = stats.get('user_stats', dict())
        self.add_gauge_value('User Cache/Slots', '',
                             user_stats.get('num_slots', 0))
        self.add_gauge_value('User Cache/Entries', '',
                             user_stats.get('num_entries', 0))
        self.add_gauge_value('User Cache/Size', 'Bytes',
                             user_stats.get('mem_size', 0))
        self.add_gauge_value('User Cache/Expunges', '',
                             user_stats.get('expunges', 0))

        hits = user_stats.get('num_hits', 0)
        misses = user_stats.get('num_misses', 0)
        total = hits + misses
        if total > 0:
            effectiveness = float(float(hits) / float(total)) * 100
        else:
            effectiveness = 0
        self.add_gauge_value('User Cache/Effectiveness', '%', effectiveness)

        self.add_derive_value('User Cache/Hits', '', hits)
        self.add_derive_value('User Cache/Misses', '', misses)
        self.add_derive_value('User Cache/Inserts', '',
                              user_stats.get('num_inserts', 0))
