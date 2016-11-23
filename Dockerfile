FROM armv7/armhf-ubuntu
MAINTAINER Shawn Nock <nock@nocko.se>

ENV APPNAME c3next

RUN apt-get update && apt-get install -y --no-install-recommends \
	python-virtualenv pypy libffi6 openssl libpq-dev gcc \
	&& rm -rf /var/lib/apt/lists/*

WORKDIR /home/$APPNAME
COPY . ./
RUN python -m virtualenv -p /usr/bin/pypy /appenv
RUN . /appenv/bin/activate; pip install -e .
CMD twistd -n -y src/$APPNAME/main.py
