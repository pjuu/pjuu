FROM alpine:latest
LABEL maintainer ant@pjuu.com

RUN apk add --no-cache --virtual .builddeps build-base python-dev wget curl git && \
    apk add --no-cache python py-virtualenv imagemagick

RUN mkdir -p /data/conf /data/pjuu

WORKDIR /data

# add stuff to image requirements, entrypoint and pjuu src
ADD ./requirements-base.txt /data/requirements-base.txt
ADD ./pjuu /data/pjuu

RUN virtualenv /data/venv
RUN /data/venv/bin/pip install -r /data/requirements-base.txt

