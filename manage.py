#!/usr/bin/env python
# -*- coding: utf8 -*-

"""Pjuu specific CLI commands. For running test suite, coverage, flake
and development server.

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2016 Joe Doherty

"""

import sys
import unittest

import click
import coverage
from flask.cli import FlaskGroup

from pjuu import create_app


@click.group(cls=FlaskGroup, create_app=create_app)
def cli():
    """Management file"""
    pass


@cli.command()
def test():
    """Runs unit tests with code coverage"""
    # Start coverage
    cov = coverage.Coverage(source=['pjuu'], branch=True,
                            omit=['pjuu/wsgi.py', '*.html', '*.txt'])
    cov.start()

    # Prepare test suite
    test_loader = unittest.defaultTestLoader
    test_runner = unittest.TextTestRunner(verbosity=2)
    test_suite = test_loader.discover('tests', pattern='test_*.py')

    # Run all located tests and save the returns
    test_results = test_runner.run(test_suite)

    # Stop coverage and save the output
    cov.stop()
    cov.save()
    cov.report()

    # If we have any test failures set the return code from script to 1
    # This will allow Travis-CI to inform us that the build failed
    if not test_results.wasSuccessful():
        sys.exit(1)


@cli.command()
def flake():
    """Checks PEP8 compliance with Flake8"""
    # Flake8 does NOT have a public API
    # We will call it from the command line
    from subprocess import call
    return_code = call(["flake8", "--exclude=docs,venv,venv3,venvpypy", "."])

    # Ensure the command returns the same code as the flake8 utility
    # This is needed to CI
    sys.exit(return_code)


if __name__ == '__main__':
    cli()
