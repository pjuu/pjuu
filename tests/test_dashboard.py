# -*- coding: utf8 -*-

"""Basic tests for the base alert system. These should also be tested in each
backend test for the specific alerts that appear there.

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2015 Joe Doherty

"""

import os
import socket

from flask import url_for
from pjuu.auth.backend import create_account, activate, bite

from tests import FrontendTestCase


class DashboardTests(FrontendTestCase):
    """

    """

    def test_dashboard_view(self):
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        activate(user1)

        # Ensure we can't hit the endpoint not logged in
        # We WONT be redirected to login
        resp = self.client.get(url_for('dashboard.dashboard'))
        self.assertEqual(resp.status_code, 403)

        # Log in
        self.client.post(url_for('auth.signin'), data={
            'username': 'user1',
            'password': 'Password'
        })

        # Ensure we can't hit the endpoint if we are logged in but not op
        resp = self.client.get(url_for('dashboard.dashboard'))
        self.assertEqual(resp.status_code, 403)

        # Make the user OP
        bite(user1)

        # Check
        resp = self.client.get(url_for('dashboard.dashboard'))
        self.assertEqual(resp.status_code, 200)

        # Ensure there are some stats for the different libraries we expect
        # 'Server' is provided by the dashboard itself
        self.assertIn('Server', resp.data)

        # We can further check the 'Server' section as we need to anyway.
        self.assertIn('Hostname', resp.data)
        self.assertIn('Uname', resp.data)
        self.assertIn('Time UTC', resp.data)
        self.assertIn('Timestamp', resp.data)

        # Check the values we can
        self.assertIn(' '.join(os.uname()), resp.data)
        self.assertIn(socket.gethostname(), resp.data)

        # 'Auth' is provided by pjuu.auth
        self.assertIn('Auth', resp.data)

        # 'Posts' is provided by pjuu.posts
        self.assertIn('Posts', resp.data)

        # 'Users' does not provide ANY stats at the moment

        # Done for now. All tests for other stats should be within each pkg.
