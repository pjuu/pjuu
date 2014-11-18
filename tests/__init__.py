# -*- coding: utf8 -*-

"""
Description:
    Pjuu base test cases

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
import unittest
# 3rd party imports
from flask import current_app as app, g
# Pjuu imports
from pjuu import mongo as m, redis as r
from pjuu.lib.indexes import create_indexes


class BackendTestCase(unittest.TestCase):
    """
    This case will test ALL post backend functions.
    """

    def setUp(self):
        """Recreate our indexes inside MongoDB

        """
        create_indexes()

    def tearDown(self):
        """
        Simply flush the database. Keep it clean for other tests
        """
        r.flushdb()
        m.db.connection.drop_database('pjuu_testing')


class FrontendTestCase(unittest.TestCase):
    """
    This test case will test all the posts subpackages; views, decorators
    and forms
    """

    def setUp(self):
        """
        Flush the database and create a test client so that we can check all
        end points.
        """
        # Get our test client
        self.client = app.test_client()
        # Push a request context
        self.ctx = app.test_request_context()
        self.ctx.push()
        # Clear the token from g object, this hangs around
        g.token = None

    def tearDown(self):
        """
        Simply flush the database. Keep it clean for other tests
        """
        self.ctx.pop()
        r.flushdb()
        m.db.connection.drop_database('pjuu_testing')
