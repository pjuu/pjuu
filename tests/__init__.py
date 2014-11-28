# -*- coding: utf8 -*-

"""

"""

# Stdlib imports
import unittest
# 3rd party imports
from flask import current_app as app
# Pjuu imports
from pjuu import create_app, mongo as m, redis as r
from pjuu.lib.indexes import ensure_indexes


class BackendTestCase(unittest.TestCase):
    """This case will test ALL post backend functions.

    """

    def setUp(self):
        """Recreate our indexes inside MongoDB

        """
        # Create flask app and context
        self.app = create_app(config_dict={
            'TESTING': 'True',
            'SERVER_NAME': 'localhost',
            'WTF_CSRF_ENABLED': False,
            'MONGO_DBNAME': 'pjuu_testing',
            'REDIS_DB': 2,
            'SESSION_REDIS_DB': 3
        })
        self.app_ctx = self.app.app_context()
        self.app_ctx.push()

        r.flushdb()
        m.db.posts.remove({})
        m.db.users.remove({})

        # Ensure the MongoDB indexes are present
        ensure_indexes()

    def tearDown(self):
        """Flush the Redis database and drop the Mongo database

        """
        # Clear the databases
        r.flushdb()
        m.db.posts.remove({})
        m.db.users.remove({})

        self.app_ctx.pop()


class FrontendTestCase(BackendTestCase):

    def setUp(self):
        super(FrontendTestCase, self).setUp()

        # Push a request context
        self.req_ctx = app.test_request_context()
        self.req_ctx.push()

        # Create our test client
        self.client = app.test_client()

    def tearDown(self):
        self.req_ctx.pop()
        super(FrontendTestCase, self).tearDown()
