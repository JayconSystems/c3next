FROM armv7/armhf-ubuntu
MAINTAINER Shawn Nock <nock@nocko.se>

ENV APPNAME c3next

RUN apt-get update && apt-get install -y --no-install-recommends \
	python-virtualenv pypy libffi6 openssl \
	&& rm -rf /var/lib/apt/lists/*

WORKDIR /home/$APPNAME
COPY . ./
CMD . /appenv/bin/activate; twistd -n -y src/$APPNAME/main.py
