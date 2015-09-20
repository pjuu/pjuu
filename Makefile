# Pjuu Makefile
# Used for quickly testing, running and ensuring code quality
# during development.

all: flake cover

test:
	@echo 'Running test suite...'
	coverage run --source=pjuu --omit=pjuu/wsgi.py,*.html,*.txt --branch run_tests.py

coverage:
	@echo 'Generating code coverage report...'
	coverage report

flake:
	@echo 'Checking coding standards...'
	flake8 --exclude=docs,venv,venv3,venvpypy .

run:
	@echo 'Starting Pjuu test server...'
	python run_server.py
