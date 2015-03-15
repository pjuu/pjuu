FROM debian:wheezy
MAINTAINER Joe Doherty <joe@pjuu.com>

# Install all system requirements
ENV DEBIAN_FRONTEND noninteractive
RUN apt-get update && \
    apt-get -y install build-essential python-dev python-setuptools \
    libtiff4-dev libjpeg8-dev zlib1g-dev libfreetype6-dev liblcms2-dev \
    libwebp-dev tcl8.5-dev tk8.5-dev python-tk 

RUN easy_install virtualenv
RUN mkdir -p /app/conf /app/pjuu

WORKDIR /app

# PIP stuff
COPY ./requirements-base.txt /app/requirements-base.txt
COPY ./requirements-prod.txt /app/requirements-prod.txt

RUN virtualenv /app/venv
RUN venv/bin/pip install -r /app/requirements-prod.txt

# Copy the Pjuu source code, "pjuu/" in the Github ptoject
COPY ./pjuu /app/pjuu

# Pjuu needs config from the host!
VOLUME ["/app/conf"]

# Gunicorn available to the Docker container
EXPOSE 8000

# Run Gunicorn
ENTRYPOINT ["venv/bin/gunicorn"]
CMD ["-c/app/conf/gunicorn.py", "pjuu.wsgi"]
