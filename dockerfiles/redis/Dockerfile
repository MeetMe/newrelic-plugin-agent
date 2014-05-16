FROM gavinmroy/nrpadev
MAINTAINER gavinmroy@gmail.com

# Maintain our own redis user and group
RUN /usr/sbin/groupadd -r -g 107 redis
RUN /usr/sbin/useradd -M -r -u 107 -g redis redis -d /var/lib/redis

RUN apt-get update
RUN apt-get install redis-server
RUN touch /var/log/redis/.no-delete
RUN chown -R redis:root /var/log/redis
RUN chmod -R g+rw /var/log/redis
ADD redis.conf /etc/redis/redis.conf

RUN mkdir /etc/service/redis
ADD redis.sh /etc/service/redis/run

EXPOSE 6379
VOLUME	["/var/log/redis"]
