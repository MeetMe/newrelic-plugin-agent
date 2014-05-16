#! /bin/bash

set -e

if env | grep -q "DOCKER_RIAK_DEBUG"; then
  set -x
fi

DOCKER_RIAK_CLUSTER_SIZE=${DOCKER_RIAK_CLUSTER_SIZE:-5}

if docker ps -a | grep "nrpa/riak" >/dev/null; then
  echo ""
  echo "It looks like you already have some Riak containers running."
  echo "Please take them down before attempting to bring up another"
  echo "cluster with the following command:"
  echo ""
  echo "  make stop-cluster"
  echo ""

  exit 1
fi

echo
echo "Bringing up cluster nodes:"
echo

for index in $(seq -f "%02g" "1" "${DOCKER_RIAK_CLUSTER_SIZE}");
do
  if [ "${index}" -gt "1" ] ; then
    docker run -e "DOCKER_RIAK_CLUSTER_SIZE=${DOCKER_RIAK_CLUSTER_SIZE}" \
               -e "DOCKER_RIAK_AUTOMATIC_CLUSTERING=${DOCKER_RIAK_AUTOMATIC_CLUSTERING}" \
               -e NEWRELIC_KEY=$NEWRELIC_KEY \
               -e NODE_name="riak${index}" \
               -P --name "riak${index}" \
               --link "riak01" \
               --volumes-from SOURCE \
               -d nrpa/riak > /dev/null 2>&1
  else
    docker run -e "DOCKER_RIAK_CLUSTER_SIZE=${DOCKER_RIAK_CLUSTER_SIZE}" \
               -e "DOCKER_RIAK_AUTOMATIC_CLUSTERING=${DOCKER_RIAK_AUTOMATIC_CLUSTERING}" \
               -e NEWRELIC_KEY=$NEWRELIC_KEY \
               -e NODE_name="riak${index}" \
               --volumes-from SOURCE \
               -P --name "riak${index}" \
               -d nrpa/riak > /dev/null 2>&1
  fi

  CONTAINER_ID=$(docker ps | egrep "riak${index}[^/]" | cut -d" " -f1)
  CONTAINER_PORT=$(docker port "${CONTAINER_ID}" 8098 | cut -d ":" -f2)

  until curl -s "http://127.0.0.1:${CONTAINER_PORT}/ping" | grep "OK" > /dev/null 2>&1;
  do
    sleep 3
  done

  echo "  Successfully brought up [riak${index}]"
done

echo
echo "Please wait approximately 30 seconds for the cluster to stabilize."
echo
