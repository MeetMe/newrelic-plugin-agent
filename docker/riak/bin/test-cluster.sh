#! /bin/bash

set -e

if env | grep -q "DOCKER_RIAK_DEBUG"; then
  set -x
fi

RANDOM_CONTAINER_ID=$(docker ps | egrep "nrpa/riak" | cut -d" " -f1 | perl -MList::Util=shuffle -e'print shuffle<>' | head -n1)
CONTAINER_HTTP_PORT=$(docker port "${RANDOM_CONTAINER_ID}" 8098 | cut -d ":" -f2)

curl -s "http://127.0.0.1:${CONTAINER_HTTP_PORT}/stats" | python -mjson.tool
