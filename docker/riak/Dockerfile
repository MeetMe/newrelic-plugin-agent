#
# Riak Dockerfile copied mostly from https://github.com/hectcastro/docker-riak
#

FROM nrpa/base
MAINTAINER gavinmroy@gmail.com

# Environmental variables
ENV DEBIAN_FRONTEND noninteractive
ENV RIAK_VERSION 1.4.8
ENV RIAK_SHORT_VERSION 1.4

# Maintain our own riak user and group
RUN /usr/sbin/groupadd -r -g 108 riak
RUN /usr/sbin/useradd -M -r -u 108 -g riak riak -d /var/lib/riak

RUN curl -s http://apt.basho.com/gpg/basho.apt.key | apt-key add --
RUN echo "deb http://apt.basho.com precise main" > /etc/apt/sources.list.d/basho.list
RUN apt-get update

RUN apt-get install -y riak erlang git
RUN sed -i.bak 's/127.0.0.1/0.0.0.0/' /etc/riak/app.config
RUN echo "ulimit -n 4096" >> /etc/default/riak

ADD bin/automatic_clustering.sh /etc/my_init.d/99_automatic_clustering.sh

# Tune Riak configuration settings for the container
RUN sed -i.bak 's/127.0.0.1/0.0.0.0/' /etc/riak/app.config && \
    sed -i.bak 's/{anti_entropy_concurrency, 2}/{anti_entropy_concurrency, 1}/' /etc/riak/app.config && \
    sed -i.bak 's/{map_js_vm_count, 8 }/{map_js_vm_count, 0 }/' /etc/riak/app.config && \
    sed -i.bak 's/{reduce_js_vm_count, 6 }/{reduce_js_vm_count, 0 }/' /etc/riak/app.config && \
    sed -i.bak 's/{hook_js_vm_count, 2 }/{hook_js_vm_count, 0 }/' /etc/riak/app.config && \
    sed -i.bak "s/##+zdbbl/+zdbbl/" /etc/riak/vm.args

RUN mkdir /etc/service/riak
ADD bin/riak.sh /etc/service/riak/run

ADD bin/newrelic-plugin-agent.sh /etc/service/newrelic-plugin-agent/run
ADD newrelic-plugin-agent.cfg /etc/newrelic/newrelic-plugin-agent.cfg

RUN git clone https://github.com/basho/basho_bench.git /opt/basho_bench
RUN cd /opt/basho_bench && make all

RUN apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

EXPOSE 8098 8087
