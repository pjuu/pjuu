FROM pjuu/pjuu:base
LABEL maintainer Joe Doherty <joe@pjuu.com>

# Gunicorn available to the Docker container
EXPOSE 8000

# Run Gunicorn
ENTRYPOINT ["/data/venv/bin/gunicorn"]
CMD ["-b 0.0.0.0:8000", "-k gevent", "pjuu.wsgi:application"]
