FROM gavinmroy/nrpadev
MAINTAINER gavinmroy@gmail.com

# Maintain our own riak user and group
RUN /usr/sbin/groupadd -r -g 108 riak
RUN /usr/sbin/useradd -M -r -u 108 -g riak riak -d /var/lib/riak

RUN curl -s http://apt.basho.com/gpg/basho.apt.key | apt-key add --
RUN echo "deb http://apt.basho.com $(lsb_release -cs) main" > /etc/apt/sources.list.d/basho.list
RUN apt-get update

RUN apt-get install -y riak
RUN sed -i.bak 's/127.0.0.1/0.0.0.0/' /etc/riak/app.config
RUN echo "ulimit -n 4096" >> /etc/default/riak

RUN mkdir /etc/service/riak
ADD riak.sh /etc/service/riak/run

EXPOSE 8087 8098 22
VOLUME	["/var/log/riak"]
