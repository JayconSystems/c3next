FROM armv7/armhf-ubuntu
MAINTAINER Shawn Nock <nock@nocko.se>

ENV APPNAME c3next

RUN gpg --keyserver pool.sks-keyservers.net --recv-keys B42F6819007F00F88E364FD4036A9C25BF357DD4
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
	wget \
	pypy \
	dirmngr \
	&& rm -rf /var/lib/apt/lists/* \
	&& wget -O /usr/local/bin/gosu "https://github.com/tianon/gosu/releases/download/1.2/gosu-$(dpkg --print-architecture)" \
	&& wget -O /usr/local/bin/gosu.asc "https://github.com/tianon/gosu/releases/download/1.2/gosu-$(dpkg --print-architecture).asc" \
	&& gpg --verify /usr/local/bin/gosu.asc \
	&& rm /usr/local/bin/gosu.asc \
	&& chmod +x /usr/local/bin/gosu \
	&& apt-get purge -y --auto-remove wget

RUN useradd -m $APPNAME
WORKDIR /home/$APPNAME

COPY . ./
RUN pip install -e .
CMD exec gosu $APPNAME twistd -n -y src/$APPNAME/main.py
