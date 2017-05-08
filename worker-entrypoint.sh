#!/bin/sh

PJUU_SETTINGS=/data/conf/pjuu.conf /data/venv/bin/celery worker -A pjuu.celery_app
