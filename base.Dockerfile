FROM alpine:3.9
LABEL maintainer ant@pjuu.com

ENV MAGICK_HOME=/usr

RUN apk add --no-cache --virtual .build-deps build-base wget curl git && \
    apk add --no-cache python3 python3-dev py-virtualenv imagemagick imagemagick-dev

RUN mkdir -p /data/conf /data/pjuu

WORKDIR /data

# add stuff to image requirements, entrypoint and pjuu src
ADD ./requirements-base.txt /data/requirements-base.txt
ADD ./pjuu /data/pjuu

RUN virtualenv -p python3 /data/venv
RUN /data/venv/bin/pip install -r /data/requirements-base.txt

RUN apk del .build-deps

