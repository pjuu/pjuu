#!/usr/bin/env python
# -*- coding: utf8 -*-

"""Runs Pjuu's test suite.

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2020 Joe Doherty

"""

# Stdlib imports
import sys
import unittest


if __name__ == '__main__':
    """ Run Pjuu's unittests. This will return 1 on failure to be compatible
    with Travis-CI.

    """
    # Prepare for testing
    test_loader = unittest.defaultTestLoader
    test_runner = unittest.TextTestRunner(verbosity=2)
    test_suite = test_loader.discover('tests', pattern='test_*.py')

    # Run all located tests and save the returns
    test_results = test_runner.run(test_suite)

    # If we have any test failures set the return code from script to 1
    # This will allow Travis-CI to inform us that the build failed
    if not test_results.wasSuccessful():
        sys.exit(1)
