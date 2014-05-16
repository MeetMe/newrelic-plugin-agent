#! /bin/sh

if env | grep -q "DOCKER_RIAK_AUTOMATIC_CLUSTERING=1"; then
  # Join node to the cluster
  (sleep 5; if env | grep -q "SEED_PORT_8098_TCP_ADDR"; then
    riak-admin cluster join "riak@${SEED_PORT_8098_TCP_ADDR}" > /dev/null 2>&1
  fi) &

  # Are we the last node to join?
  (sleep 8; if riak-admin member-status | egrep "joining|valid" | wc -l | grep -q "${DOCKER_RIAK_CLUSTER_SIZE}"; then
    riak-admin cluster plan > /dev/null 2>&1 && riak-admin cluster commit > /dev/null 2>&1
  fi) &
fi
