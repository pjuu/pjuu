FROM python:3.8-slim-buster

ENV MAGICK_HOME=/usr

RUN apt-get update && \
    apt-get -y install build-essential python3-dev pipenv libmagickwand-dev

RUN mkdir -p /data
WORKDIR /data

COPY ./Pipfile ./Pipfile.lock ./
RUN pipenv install --system --deploy --ignore-pipfile

ADD ./pjuu ./pjuu

EXPOSE 8000

ENTRYPOINT ["gunicorn"]
CMD ["-b", "0.0.0.0:8000", "-k", "gevent", "pjuu.wsgi:application"]
