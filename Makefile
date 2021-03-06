# Pjuu Makefile
# Used for quickly testing, running and ensuring code quality
# during development.

all: flake test coverage

test:
	@echo 'Running test suite...'
	coverage run --source=pjuu --omit=pjuu/wsgi.py,pjuu/celery_app.py,*.html,*.txt --branch run_tests.py
	coverage xml
	coverage html
	coverage report

flake:
	@echo 'Checking coding standards...'
	flake8 --exclude=docs,venv,venv3,venvpypy .

run:
	@echo 'Starting Pjuu (Gunicorn with Gevent)...'
	gunicorn -b 0.0.0.0:5000 -w 1 -k gevent --reload --access-logfile=- --access-logformat='%(r)s %(D)sus' dev_server:application

celery:
	@echo 'Starting Pjuu Worker (Celery)...'
	celery -A pjuu.celery_app worker
