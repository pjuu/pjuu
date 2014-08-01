#!/usr/bin/env python
# -*- coding: utf8 -*-

"""
Description:
    Runs Pjuu's tests

    This script will ensure that all relevant settings are applied to Pjuu to
    allow these too run. You may need to change this file to fit your own needs

    We use Redis db's 0 & 1 for our dev environemtn and 2 & 3 for the automated
    unittests. This may not fit your needs.

Licence:
    Copyright 2014 Joe Doherty <joe@pjuu.com>

    Pjuu is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    Pjuu is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

# Stdlib imports
import sys
import unittest
# Pjuu imports
from pjuu import create_app


if __name__ == '__main__':
    """
    Run Pjuu's unittests. This will return 1 on failure to be compatible with
    Travis-CI.

    Note: If there are major errors this may never get round to returning
          a 1 please be careful. Tavis-CI may think the tests have passed
    Note: This may change to pytest or nosetest in the future.
    """
    # Create our testing app with explicit test settings
    # These are for our uses when deploying so that Travis-CI will run the
    # the unittest's.
    app = create_app(config_dict={
        # Testing needs to be enabled so that we can get passed the
        # in tests and also so Flask-Mail does not send mail
        'TESTING': 'True',
        # We need a SERVER_NAME so that we can use url_for()
        'SERVER_NAME': 'localhost',
        # This just stops us getting through forms if True
        'WTF_CSRF_ENABLED': False,
        # Change the Redis database numbers so that we do not overwrite
        # our data each time we run the tests
        'REDIS_DB': 2,
        'SESSION_REDIS_DB': 3
    })

    # Create a request context to run all of the tests in.
    # The FrontendTests in each module will create a test request context
    # before each test and pop it afterwards
    with app.app_context():
        # Prepare for testing
        test_loader = unittest.defaultTestLoader
        test_runner = unittest.TextTestRunner()
        test_suite = test_loader.discover('pjuu', pattern='tests.py')

        # Run all located tests and save the returns
        test_results = test_runner.run(test_suite)

        # If we have any test failures set the return code from script to 1
        # This will allow Travis-CI to inform us that the build failed
        if not test_results.wasSuccessful():
            sys.exit(1)
