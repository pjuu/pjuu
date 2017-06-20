FROM pjuu/pjuu:base
LABEL maintainer ant@pjuu.com

WORKDIR /data

ADD ./worker-entrypoint.sh /data/worker-entrypoint.sh

RUN chmod +x worker-entrypoint.sh

# Run Celery
ENTRYPOINT /data/worker-entrypoint.sh
