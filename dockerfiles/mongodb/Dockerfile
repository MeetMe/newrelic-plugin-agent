FROM gavinmroy/nrpadev
MAINTAINER gavinmroy@gmail.com

# Maintain our own mongodb user and group
RUN /usr/sbin/groupadd -r -g 106 mongodb
RUN /usr/sbin/useradd -M -r -u 106 -g mongodb mongodb -d /var/lib/mongodb

RUN apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 7F0CEB10
RUN echo 'deb http://downloads-distro.mongodb.org/repo/ubuntu-upstart dist 10gen' > /etc/apt/sources.list.d/10gen.list
RUN apt-get update && apt-get install mongodb-10gen

RUN mkdir /etc/service/mongodb
ADD mongodb.sh /etc/service/mongodb/run

EXPOSE 27017 28017
VOLUME	["/var/log/mongodb"]
