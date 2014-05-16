"""
PHP APC Support

"""
import logging

from newrelic_plugin_agent.plugins import base

LOGGER = logging.getLogger(__name__)


class APC(base.JSONStatsPlugin):

    GUID = 'com.meetme.newrelic_php_apc_agent'

    def add_datapoints(self, stats):
        """Add all of the data points for a node

        :param dict stats: The stats content from APC as a string

        """
        # APC Shared Memory Stats
        shared_memory = stats.get('shared_memory', dict())
        self.add_gauge_value('Shared Memory/Available', 'bytes',
                             shared_memory.get('avail_mem', 0))
        self.add_gauge_value('Shared Memory/Segment Size', 'bytes',
                             shared_memory.get('seg_size', 0))
        self.add_gauge_value('Shared Memory/Segment Count', 'segments',
                             shared_memory.get('nseg',
                                               shared_memory.get('num_seg',
                                                                 0)))

        # APC System Stats
        system_stats = stats.get('system_stats', dict())
        self.add_gauge_value('System Cache/Slots', 'slots',
                             system_stats.get('nslots',
                                              system_stats.get('num_slots',
                                                               0)))
        self.add_gauge_value('System Cache/Entries', 'files',
                             system_stats.get('nentries',
                                              system_stats.get('num_entries',
                                                               0)))
        self.add_gauge_value('System Cache/Size', 'bytes',
                             system_stats.get('mem_size', 0))
        self.add_gauge_value('System Cache/Expunges', 'files',
                             system_stats.get('nexpunges',
                                              system_stats.get('num_expunges',
                                                               0)))

        hits = system_stats.get('nhits', system_stats.get('num_hits', 0))
        misses = system_stats.get('nmisses', system_stats.get('num_misses', 0))
        total = hits + misses
        if total > 0:
            effectiveness = float(float(hits) / float(total)) * 100
        else:
            effectiveness = 0
        self.add_gauge_value('System Cache/Effectiveness', 'percent',
                             effectiveness)

        self.add_derive_value('System Cache/Hits', 'files', hits)
        self.add_derive_value('System Cache/Misses', 'files', misses)
        self.add_derive_value('System Cache/Inserts', 'files',
                              system_stats.get('ninserts',
                                               system_stats.get('num_inserts',
                                                                0)))

        # APC User Stats
        user_stats = stats.get('user_stats', dict())
        self.add_gauge_value('User Cache/Slots', 'slots',
                             user_stats.get('nslots',
                                            user_stats.get('num_slots', 0)))
        self.add_gauge_value('User Cache/Entries', 'keys',
                             user_stats.get('nentries',
                                            user_stats.get('num_entries', 0)))
        self.add_gauge_value('User Cache/Size', 'bytes',
                             user_stats.get('mem_size', 0))
        self.add_gauge_value('User Cache/Expunges', 'keys',
                             user_stats.get('nexpunges',
                                            user_stats.get('num_expunges', 0)))

        hits = user_stats.get('nhits', user_stats.get('num_hits', 0))
        misses = user_stats.get('nmisses', user_stats.get('num_misses', 0))
        total = hits + misses
        if total > 0:
            effectiveness = float(float(hits) / float(total)) * 100
        else:
            effectiveness = 0
        self.add_gauge_value('User Cache/Effectiveness', 'percent',
                             effectiveness)

        self.add_derive_value('User Cache/Hits', 'keys', hits)
        self.add_derive_value('User Cache/Misses', 'keys', misses)
        self.add_derive_value('User Cache/Inserts', 'keys',
                              user_stats.get('ninserts',
                                             user_stats.get('num_inserts',0)))
