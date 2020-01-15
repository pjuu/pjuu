# -*- coding: utf8 -*-

"""Basic tests for the base alert system. These should also be tested in each
backend test for the specific alerts that appear there.

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2020 Joe Doherty

"""

import os
import socket

from flask import url_for
from pjuu.auth.backend import create_account, activate, bite
from pjuu.posts.backend import create_post, flag_post

from tests import FrontendTestCase


class DashboardTests(FrontendTestCase):
    """

    """

    def test_dashboard_view(self):
        """Ensure basic stats show in dashboard"""
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
        self.assertIn('Server', resp.get_data(as_text=True))

        # We can further check the 'Server' section as we need to anyway.
        self.assertIn('Hostname', resp.get_data(as_text=True))
        self.assertIn('Uname', resp.get_data(as_text=True))
        self.assertIn('Time UTC', resp.get_data(as_text=True))
        self.assertIn('Timestamp', resp.get_data(as_text=True))

        # Check the values we can
        self.assertIn(' '.join(os.uname()), resp.get_data(as_text=True))
        self.assertIn(socket.gethostname(), resp.get_data(as_text=True))

        # 'Auth' is provided by pjuu.auth
        self.assertIn('Auth', resp.get_data(as_text=True))

        # 'Posts' is provided by pjuu.posts
        self.assertIn('Posts', resp.get_data(as_text=True))

        # 'Users' does not provide ANY stats at the moment

        # Done for now. All tests for other stats should be within each pkg.

    def test_flag_control(self):
        """Ensure flagged posts appear in the dashboard"""
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        user2 = create_account('user2', 'user2@pjuu.com', 'Password')

        # Make user1 OP
        bite(user1)
        activate(user1)

        post1 = create_post(user2, 'user2', 'post1')
        post2 = create_post(user2, 'user2', 'post2')

        comment1 = create_post(user2, 'user2', 'comment1', post1)
        comment2 = create_post(user2, 'user2', 'comment2', post1)

        # Flag all the posts
        flag_post(user1, post1)
        flag_post(user1, post2)
        flag_post(user1, comment1)
        flag_post(user1, comment2)

        self.client.post(url_for('auth.signin'), data={
            'username': 'user1',
            'password': 'Password'
        })
        resp = self.client.get(url_for('dashboard.dashboard'))

        s = '{0} - <a href="{1}">{2}</a>: <a href="{3}">{4}</a> ' + \
            '[<a href="{5}">Unflag</a>]'

        self.assertIn(s.format(
            1,
            url_for('users.profile',
                    username='user2'),
            'user2',
            url_for('posts.view_post',
                    username='user2',
                    post_id=post1),
            post1,
            url_for('posts.unflag_post', post_id=post1)
        ), resp.get_data(as_text=True))

        self.assertIn(s.format(
            1,
            url_for('users.profile',
                    username='user2'),
            'user2',
            url_for('posts.view_post',
                    username='user2',
                    post_id=post1),
            comment1,
            url_for('posts.unflag_post', post_id=comment1)
        ) + ' (comment)', resp.get_data(as_text=True))
