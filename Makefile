# Quick make commands to ensure all commands for checking code have been run
# To check everything just run `make`

all: flake cover

test:
	@echo 'Running tests...'
	python run_tests.py

cover:
	@echo 'Ensuring all lines of code are checked by the tests...'
	coverage run --source=pjuu --omit=pjuu/wsgi.py,*.html,*.txt run_tests.py
	coverage report

flake:
	@echo 'Ensuring all code is PEP8 compliant...'
	flake8 --exclude=docs,venv .

run:
	@echo 'Running Pjuu in CherryPy development server...'
	python run_server.py
