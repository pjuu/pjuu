FROM python:3.8-slim-buster

RUN apt-get update && \
    apt-get -y install libmagickwand-6.q16-6

RUN pip install pipenv
COPY ./Pipfile ./Pipfile.lock ./
RUN pipenv install --deploy --system

ADD ./pjuu ./pjuu

EXPOSE 8000
ENTRYPOINT ["gunicorn"]
CMD ["-b", "0.0.0.0:8000", "-k", "gevent", "pjuu.wsgi:application"]
