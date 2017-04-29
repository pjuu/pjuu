FROM debian:jessie
MAINTAINER Joe Doherty <joe@pjuu.com>

# Install all system requirements
ENV DEBIAN_FRONTEND noninteractive
RUN apt-get update && \
    apt-get -y -qq install openssl ca-certificates build-essential python-dev python-setuptools \
    libmagickwand-dev && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN easy_install virtualenv
RUN mkdir -p /data/conf /data/pjuu

WORKDIR /data

# PIP stuff
COPY ./requirements-base.txt /data/requirements-base.txt

RUN virtualenv /data/venv
RUN /data/venv/bin/pip install -r /data/requirements-base.txt

# Copy the Pjuu source code, "pjuu/" in the current directory
COPY ./pjuu /data/pjuu

# Pjuu needs config from the host!
VOLUME ["/data/conf"]

# Gunicorn available to the Docker container
EXPOSE 8000

# Run Gunicorn
ENTRYPOINT ["/data/venv/bin/celery"]
CMD ["multi", "start" "worker", "-A pjuu.celery_app", "--loglevel=INFO"]
