#!/usr/bin/env python
# -*- coding: utf8 -*-

##############################################################################
# Copyright 2014 Joe Doherty <joe@pjuu.com>
#
# Pjuu is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Pjuu is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
##############################################################################

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
	      a 0 please be careful.
	Note: This may change to pytest in the future.
	"""
	app = create_app('settings.py')
	with app.app_context():
		# Prepare for testing
		test_loader = unittest.defaultTestLoader
		test_runner =  unittest.TextTestRunner()
		test_suite = test_loader.discover('pjuu', pattern='tests.py')

		# Run all located tests and save the returns
		test_results = test_runner.run(test_suite)

		# If we have any test failures set the return code from script to 1
		# This will allow Travis-CI to inform us that the build failed
		if test_results.failures:
			sys.exit(1)