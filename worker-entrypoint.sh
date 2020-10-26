#!/bin/sh

PJUU_SETTINGS=/data/conf/pjuu.conf /data/venv/bin/celery -A pjuu.celery_app worker
