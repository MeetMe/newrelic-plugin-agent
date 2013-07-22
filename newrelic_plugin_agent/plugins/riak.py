"""
Riak Plugin

"""
import logging

from newrelic_plugin_agent.plugins import base

LOGGER = logging.getLogger(__name__)


class Riak(base.JSONStatsPlugin):

    DEFAULT_PATH = '/stats'
    GUID = 'com.meetme.newrelic_riak_agent'

    def add_datapoints(self, stats):
        """Add all of the data points for a node

        :param dict stats: all of the nodes

        """
        self.add_gauge_value('Delays/Convergence', 'us',
                             stats.get('converge_delay_total', 0),
                             min_val=stats.get('converge_delay_min', 0),
                             max_val=stats.get('converge_delay_max', 0))
        self.add_gauge_value('Delays/Rebalance', 'us',
                             stats.get('rebalance_delay_total', 0),
                             min_val=stats.get('rebalance_delay_min', 0),
                             max_val=stats.get('rebalance_delay_max', 0))

        self.add_gauge_value('FSM/Object Size/Mean', 'bytes',
                             stats.get('node_get_fsm_objsize_mean', 0))
        self.add_gauge_value('FSM/Object Size/Median', 'bytes',
                             stats.get('node_get_fsm_objsize_median', 0))
        self.add_gauge_value('FSM/Object Size/90th Percentile', 'bytes',
                             stats.get('node_get_fsm_objsize_90', 0))
        self.add_gauge_value('FSM/Object Size/95th Percentile', 'bytes',
                             stats.get('node_get_fsm_objsize_95', 0))
        self.add_gauge_value('FSM/Object Size/100th Percentile', 'bytes',
                             stats.get('node_get_fsm_objsize_100', 0))

        self.add_gauge_value('FSM/Siblings/Mean', '',
                             stats.get('node_get_fsm_siblings_mean', 0))
        self.add_gauge_value('FSM/Siblings/Mean', '',
                             stats.get('node_get_fsm_siblings_media', 0))
        self.add_gauge_value('FSM/Siblings/90th Percentile', '',
                             stats.get('node_get_fsm_siblings_90', 0))
        self.add_gauge_value('FSM/Siblings/95th Percentile', '',
                             stats.get('node_get_fsm_siblings_95', 0))
        self.add_gauge_value('FSM/Siblings/100th Percentile', '',
                             stats.get('node_get_fsm_siblings_100', 0))

        self.add_gauge_value('FSM/Time/Get/Mean', 'us',
                             stats.get('node_get_fsm_time_mean', 0))
        self.add_gauge_value('FSM/Time/Get/Median', 'us',
                             stats.get('node_get_fsm_time_media', 0))
        self.add_gauge_value('FSM/Time/Get/90th Percentile', 'us',
                             stats.get('node_get_fsm_time_90', 0))
        self.add_gauge_value('FSM/Time/Get/95th Percentile', 'us',
                             stats.get('node_get_fsm_time_95', 0))
        self.add_gauge_value('FSM/Time/Get/100th Percentile', 'us',
                             stats.get('node_get_fsm_time_100', 0))

        self.add_gauge_value('FSM/Time/Put/Mean', 'us',
                             stats.get('node_put_fsm_time_mean', 0))
        self.add_gauge_value('FSM/Time/Put/Median', 'us',
                             stats.get('node_put_fsm_time_media', 0))
        self.add_gauge_value('FSM/Time/Put/90th Percentile', 'us',
                             stats.get('node_put_fsm_time_90', 0))
        self.add_gauge_value('FSM/Time/Put/95th Percentile', 'us',
                             stats.get('node_put_fsm_time_95', 0))
        self.add_gauge_value('FSM/Time/Put/100th Percentile', 'us',
                             stats.get('node_put_fsm_time_100', 0))

        self.add_derive_value('Failures/Pre-commit', '',
                              stats.get('precommit_fail', 0))
        self.add_derive_value('Failures/Post-commit', '',
                              stats.get('postcommit_fail', 0))

        self.add_derive_value('Gossip/Ignored', '',
                              stats.get('ignored_gossip_total', 0))
        self.add_derive_value('Gossip/Received', '',
                              stats.get('gossip_received', 0))

        self.add_derive_value('Handoff Timeouts', '',
                              stats.get('handoff_timeouts', 0))

        self.add_gauge_value('Mappers/Executing', '',
                             stats.get('executing_mappers', 0))

        self.add_gauge_value('Memory/Allocated', 'bytes',
                             stats.get('mem_allocated', 0))
        self.add_gauge_value('Memory/Total', 'bytes',
                             stats.get('mem_total', 0))
        self.add_gauge_value('Memory/Erlang/Atom/Allocated', 'bytes',
                             stats.get('memory_atom', 0))
        self.add_gauge_value('Memory/Erlang/Atom/Used', 'bytes',
                             stats.get('memory_atom_used', 0))
        self.add_gauge_value('Memory/Erlang/Binary', 'bytes',
                             stats.get('memory_binary', 0))
        self.add_gauge_value('Memory/Erlang/Code', 'bytes',
                             stats.get('memory_code', 0))
        self.add_gauge_value('Memory/Erlang/ETS', 'bytes',
                             stats.get('memory_ets', 0))
        self.add_gauge_value('Memory/Erlang/Processes/Allocated', 'bytes',
                             stats.get('memory_processes', 0))
        self.add_gauge_value('Memory/Erlang/Processes/Used', 'bytes',
                             stats.get('memory_processes_used', 0))
        self.add_gauge_value('Memory/Erlang/System', 'bytes',
                             stats.get('memory_system', 0))
        self.add_gauge_value('Memory/Erlang/Total', 'bytes',
                             stats.get('memory_total', 0))

        self.add_gauge_value('Nodes/Connected', '',
                             len(stats.get('connected_nodes', list())))

        self.add_gauge_value('Pipeline/Active', '',
                             stats.get('pipeline_active', 0))
        self.add_derive_value('Pipeline/Created', '',
                              stats.get('pipeline_create_count', 0))
        self.add_derive_value('Pipeline/Creation Errors', '',
                              stats.get('pipeline_create_error_count', 0))

        self.add_gauge_value('Processes/OS', '',
                             stats.get('cpu_nprocs', 0))

        self.add_gauge_value('Processes/Erlang', '',
                             stats.get('cpu_nprocs', 0))

        self.add_gauge_value('Protocol Buffer Connections', 'active',
                             stats.get('pbc_active', 0))
        self.add_derive_value('Protocol Buffer Connections', 'total',
                              stats.get('pbc_connects_total', 0))

        self.add_derive_value('Read Repairs', '',
                              stats.get('read_repairs_total', 0))

        self.add_derive_value('Requests/Gets', '',
                              stats.get('node_gets_total', 0))
        self.add_derive_value('Requests/Puts', '',
                              stats.get('node_puts_total', 0))
        self.add_derive_value('Requests/Redirected', '',
                              stats.get('coord_redirs_total', 0))


        self.add_gauge_value('Ring/Members', '',
                             len(stats.get('ring_members', list())))
        self.add_gauge_value('Ring/Partitions', '',
                             stats.get('ring_num_partitions', 0))
        self.add_gauge_value('Ring/Size', '',
                             stats.get('ring_creation_size', 0))
        self.add_derive_value('Ring/Reconciled', '',
                              stats.get('rings_reconciled_total', 0))

        self.add_derive_value('VNodes/Gets', '',
                              stats.get('vnode_gets_total', 0))
        self.add_derive_value('VNodes/Puts', '',
                              stats.get('vnode_puts_total', 0))

        self.add_derive_value('VNodes/Index', '',
                              stats.get('vnode_index_deletes_total', 0))
        self.add_derive_value('VNodes/Index', '',
                              stats.get('vnode_index_deletes_postings_total',
                                        0))
        self.add_derive_value('VNodes/Index', '',
                              stats.get('vnode_index_reads_total', 0))
        self.add_derive_value('VNodes/Index', '',
                              stats.get('vnode_index_writes_total', 0))
        self.add_derive_value('VNodes/Index', '',
                              stats.get('vnode_writes_postings_total', 0))
