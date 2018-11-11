FROM alpine:3.5
LABEL maintainer ant@pjuu.com

ENV MAGICK_HOME=/usr

RUN apk add --no-cache --virtual .build-deps build-base python-dev wget curl git && \
    apk add --no-cache python py-virtualenv imagemagick imagemagick-dev && \
    apk add --no-cache nodejs

RUN mkdir -p /data/conf /data/pjuu

WORKDIR /data

# add stuff to image requirements, entrypoint and pjuu src
ADD ./requirements-base.txt /data/requirements-base.txt
ADD ./pjuu /data/pjuu
ADD ./gulpfile.js /data/gulpfile.js
ADD ./package.json /data/package.json

# Install NPM dependencies for building
RUN npm install -g gulp-cli && npm install && gulp

RUN virtualenv /data/venv
RUN /data/venv/bin/pip install -r /data/requirements-base.txt

RUN apk del .build-deps nodejs

