FROM python:3.8-alpine
LABEL maintainer ant@pjuu.com

ENV MAGICK_HOME=/usr

RUN apk add --no-cache --virtual .build-deps build-base wget curl git \
    libffi-dev imagemagick imagemagick-dev

RUN mkdir -p /data/conf /data/pjuu

WORKDIR /data

# add stuff to image requirements, entrypoint and pjuu src
ADD ./requirements-base.txt /data/requirements-base.txt
ADD ./pjuu /data/pjuu

RUN python3 -m venv /data/venv
RUN /data/venv/bin/pip install -r /data/requirements-base.txt

RUN apk del .build-deps
