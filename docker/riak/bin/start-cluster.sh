#! /bin/bash

set -e

if env | grep -q "DOCKER_RIAK_DEBUG"; then
  set -x
fi

RIAK_CLUSTER_SIZE=${DOCKER_RIAK_CLUSTER_SIZE:-5}
RIAK_AUTOMATIC_CLUSTERING=${DOCKER_RIAK_AUTOMATIC_CLUSTERING:-1}

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
echo "Bringing up ${RIAK_CLUSTER_SIZE} cluster nodes:"
echo

for index in $(seq -f "%02g" "1" "${RIAK_CLUSTER_SIZE}");
do
  echo "  Starting [riak${index}]"

  if [ "${index}" -gt "1" ] ; then

    docker run -e DOCKER_RIAK_CLUSTER_SIZE=${RIAK_CLUSTER_SIZE} \
               -e DOCKER_RIAK_AUTOMATIC_CLUSTERING=${RIAK_AUTOMATIC_CLUSTERING} \
               -e NEWRELIC_KEY=${NEWRELIC_KEY} \
               -h riak${index} \
               -P \
               --link=riak01:8098 \
               --name riak${index} \
               --volumes-from SOURCE \
               -d nrpa/riak > /dev/null 2>&1

  else
    docker run -e DOCKER_RIAK_CLUSTER_SIZE=${RIAK_CLUSTER_SIZE} \
               -e DOCKER_RIAK_AUTOMATIC_CLUSTERING=${RIAK_AUTOMATIC_CLUSTERING} \
               -e NEWRELIC_KEY=${NEWRELIC_KEY} \
               -h riak${index} \
               -P \
               --name riak${index} \
               --volumes-from SOURCE \
               -d nrpa/riak > /dev/null 2>&1
  fi

  CONTAINER_ID=$(docker ps | egrep "riak${index}[^/]" | cut -d" " -f1)
  CONTAINER_PORT=$(docker port "${CONTAINER_ID}" 8098 | cut -d ":" -f2)

  until curl -s "http://127.0.0.1:${CONTAINER_PORT}/ping" | grep "OK" > /dev/null 2>&1;
  do
    sleep 1
  done

  echo "  Started  [riak${index}]"
done

echo
echo "Please wait approximately 30 seconds for the cluster to stabilize."
echo
