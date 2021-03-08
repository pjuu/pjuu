FROM python:3.8-alpine

ENV MAGICK_HOME=/usr

RUN apk add --no-cache --virtual .build-deps build-base wget curl git libffi-dev && \
    apk add --no-cache imagemagick imagemagick-dev

RUN mkdir -p /data
WORKDIR /data

RUN pip3 install pipenv

COPY ./Pipfile ./Pipfile.lock ./
RUN pipenv install --system --deploy --ignore-pipfile

ADD ./pjuu ./pjuu

EXPOSE 8000

ENTRYPOINT ["gunicorn"]
CMD ["-b", "0.0.0.0:8000", "-k", "gevent", "pjuu.wsgi:application"]
