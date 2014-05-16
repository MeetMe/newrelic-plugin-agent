FROM gavinmroy/nrpadev
MAINTAINER gavinmroy@gmail.com
RUN apt-get update && apt-get install -y memcached
RUN mkdir /etc/service/memcached
ADD memcached.sh /etc/service/memcached/run
EXPOSE 11211
