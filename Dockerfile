FROM python:3.12-slim-bookworm AS builder

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        libmagickwand-dev

COPY ./requirements.txt requirements.txt

RUN python3 -m venv .venv
RUN .venv/bin/pip install -r /requirements.txt

FROM python:3.12-slim-bookworm

RUN apt-get update && \
    apt-get -y install libmagickwand-6.q16-6

COPY --from=builder .venv .venv

ADD ./pjuu ./pjuu

ENV PATH="$PATH:/.venv/bin"
EXPOSE 8000

ENTRYPOINT ["gunicorn"]
CMD ["-b", "0.0.0.0:8000", "-k", "gevent", "pjuu.wsgi:application"]
