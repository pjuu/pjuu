# -*- coding: utf8 -*-

"""
Description:
    Tests for the users package inside Pjuu.

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
import json
# 3rd party imports
from flask import current_app as app, url_for, g
# Pjuu imports
from pjuu import redis as r
from pjuu.auth.backend import create_user, delete_account, activate
from pjuu.lib import keys as K, timestamp
from pjuu.lib.alerts import AlertManager
from pjuu.posts.backend import (create_post, create_comment, TaggingAlert,
                                CommentingAlert)
from pjuu.users.backend import *
# Test imports
from tests.helpers import BackendTestCase, FrontendTestCase


class FrontendTests(FrontendTestCase):
    """
    This test case will test all the users subpackages; views, decorators
    and forms
    """

    def test_feed_profile(self):
        """
        Feed has been tested else where. This is just a formal test of this.
        We will post a lot of posts as 2 users so we can trigger pagination
        etc, etc.
        """
        # Create 2 users and have them follow each other
        self.assertEqual(create_user('test1', 'test1@pjuu.com', 'Password'), 1)
        self.assertEqual(create_user('test2', 'test2@pjuu.com', 'Password'), 2)
        self.assertTrue(activate(1))
        self.assertTrue(activate(2))
        self.assertTrue(follow_user(1, 2))
        self.assertTrue(follow_user(2, 1))

        # Both users are not following each other. Let's create 30 posts as
        # each user this will trigger a couple of Pagination pages on the feeds
        # and also trigger a page on the profile
        for i in range(0, 51):
            create_post(1, 'User 1, Post %d!' % i)
            create_post(2, 'User 2, Post %d!' % i)
        # We now have 60 posts on each feed

        # Log in as user 1 and check that they can see a couple of posts on the
        # first page
        resp = self.client.post(url_for('signin'), data={
            'username': 'test1',
            'password': 'Password'
        }, follow_redirects=True)
        # This sends us too / (feed) by defaults
        self.assertEqual(resp.status_code, 200)
        self.assertIn('User 1, Post 50!', resp.data)
        self.assertIn('User 2, Post 50!', resp.data)
        # Makre sure posts more than 25 ago (default pagination break)
        self.assertNotIn('User 1, Post 1!', resp.data)
        self.assertNotIn('User 2, Post 1!', resp.data)
        # Check the pagination button for next is there are not prev
        self.assertIn('<div class="button active next">', resp.data)
        self.assertNotIn('<div class="button active prev">', resp.data)

        # Let's go to page 2 in the pagination and check there are posts there
        resp = self.client.get(url_for('feed', page=2))

        # Check some posts are there and are not there
        self.assertIn('User 1, Post 30!', resp.data)
        self.assertIn('User 2, Post 30!', resp.data)
        self.assertNotIn('User 1, Post 10!', resp.data)
        self.assertNotIn('User 2, Post 5!', resp.data)
        # Check that both pagination buttons are there
        self.assertIn('<div class="button active next">', resp.data)
        self.assertIn('<div class="button active prev">', resp.data)

        # Let's go back to the first page
        resp = self.client.get(url_for('feed'))
        # We will delete one post and ensure that is goes missing
        self.assertIn('User 1, Post 50!', resp.data)
        # We won't check that the delete button belong to the above post
        # put we will check that there is atleast one delete button
        self.assertIn('<div class="delete">X</div>', resp.data)
        # Delete the post
        resp = self.client.get(url_for('delete_post', username='test1',
                               pid=101, next=url_for('feed')),
                               follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('User 1, Post 49!', resp.data)
        self.assertNotIn('User 1, Post 50!', resp.data)
        # Done for now

    def test_view_post(self):
        """
        Similar to above but check the same for the view_post page. This is
        mainly intended to check that comments render correctly
        """
        # Create two test users
        self.assertEqual(create_user('test1', 'test1@pjuu.com', 'Password'), 1)
        self.assertEqual(create_user('test2', 'test2@pjuu.com', 'Password'), 2)
        self.assertTrue(activate(1))
        self.assertTrue(activate(2))

        # Create a post as test1. We need this to ensure that we can not get
        # to the endpoint if we are logged out
        self.assertEqual(create_post(1, 'Test post'), 1)

        # Ensure we can't hit the endpoing
        resp = self.client.get(url_for('view_post', username='test1', pid=1),
                               follow_redirects=True)
        # Ensure we didn't get anything
        self.assertIn('You need to be logged in to view that', resp.data)

        # Let's ensure we can't GET the endpoint for commenting
        # This is a POST only view
        resp = self.client.get(url_for('comment', username='test1', pid=1),
                               follow_redirects=True)
        self.assertEqual(resp.status_code, 405)

        # Let's ensure we can't POST to the endpoint for commenting when not
        # logged in
        resp = self.client.post(url_for('comment', username='test1', pid=1),
                                data={'body': 'Test comment'},
                                follow_redirects=True)
        self.assertIn('You need to be logged in to view that', resp.data)

        # Sign in
        self.client.post(url_for('signin'), data={
            'username': 'test1',
            'password': 'Password'
        }, follow_redirects=True)

        # Ensure that we can not see the endpoint
        resp = self.client.get(url_for('view_post', username='test1', pid=1),
                               follow_redirects=True)
        self.assertIn('<!-- view:post:1 -->', resp.data)
        self.assertIn('Test post', resp.data)

        # Ensure we ourselves can comment on the post
        resp = self.client.post(url_for('comment', username='test1', pid=1),
                                data={'body': 'Test comment'},
                                follow_redirects=True)
        self.assertIn('<!-- list:comment:1 -->', resp.data)
        self.assertIn('Test comment', resp.data)

        # Let's logout and log in as test2
        self.client.get(url_for('signout'))
        self.client.post(url_for('signin'), data={
            'username': 'test2',
            'password': 'Password'
        })
        # Check that we can see the comment
        resp = self.client.get(url_for('view_post', username='test1', pid=1),
                               follow_redirects=True)
        self.assertIn('<!-- view:post:1 -->', resp.data)
        self.assertIn('Test post', resp.data)
        self.assertIn('<!-- list:comment:1 -->', resp.data)
        self.assertIn('Test comment', resp.data)

        # Let's ensure that we test2 can post a comment
        resp = self.client.post(url_for('comment', username='test1', pid=1),
                                data={'body': 'Test comment test2'},
                                follow_redirects=True)
        self.assertIn('<!-- list:comment:2 -->', resp.data)
        self.assertIn('Test comment test2', resp.data)
        # Done for now

    def test_follow_unfollow(self):
        """
        Ensure users can follow and unfollow each other, also ensure that the
        followers and following pages show the correct value
        """
        # Create 2 users and have them follow each other
        self.assertEqual(create_user('test1', 'test1@pjuu.com', 'Password'), 1)
        self.assertEqual(create_user('test2', 'test2@pjuu.com', 'Password'), 2)
        self.assertTrue(activate(1))
        self.assertTrue(activate(2))

        # Let's try and access the endpoints feature when we are not logged in
        # We should not be able to see it
        resp = self.client.get(url_for('follow', username='test1'),
                               follow_redirects=True)
        self.assertIn('You need to be logged in to view that', resp.data)
        resp = self.client.get(url_for('unfollow', username='test1'),
                               follow_redirects=True)
        self.assertIn('You need to be logged in to view that', resp.data)
        resp = self.client.get(url_for('following', username='test1'),
                               follow_redirects=True)
        self.assertIn('You need to be logged in to view that', resp.data)
        resp = self.client.get(url_for('followers', username='test1'),
                               follow_redirects=True)
        self.assertIn('You need to be logged in to view that', resp.data)

        # Ensure that test1 can follow and unfollow test2
        # Signin
        resp = self.client.post(url_for('signin'), data={
            'username': 'test1',
            'password': 'Password'
        }, follow_redirects=True)
        self.assertIn('<h1>Feed</h1>', resp.data)

        # Visit test2 and ensure followers count is 0
        resp = self.client.get(url_for('followers', username='test2'))
        self.assertIn('Followers: 0', resp.data)

        # Follow test2
        # Ensure we pass a next variable to come back to test2's followers page
        resp = self.client.get(url_for('follow', username='test2',
                               next=url_for('followers', username='test2')),
                               follow_redirects=True)
        # Ensure the flash message has informed use we are following
        self.assertIn('You have started following test2', resp.data)
        # Ensure test2's followers count has been incremented
        self.assertIn('Followers: 1', resp.data)
        # This should match inside a link (Test1 due to capitalization)
        # Not the best test but it works for now
        self.assertIn('<!-- list:user:test1 -->', resp.data)

        # Attempt to follow test2 again
        resp = self.client.get(url_for('follow', username='test2',
                               next=url_for('followers', username='test2')),
                               follow_redirects=True)
        # Check we got no confirmation
        self.assertNotIn('You have started following test2', resp.data)
        # Check that the followers count has not incremented
        self.assertIn('Followers: 1', resp.data)

        # Ensure test2 is in from YOUR (test1s) following page
        resp = self.client.get(url_for('following', username='test1'))
        self.assertNotIn('<!-- list:user:test1 -->', resp.data)

        # Unfollow test2
        # Ensure that all the previous has been reversed
        resp = self.client.get(url_for('unfollow', username='test2',
                               next=url_for('followers', username='test2')),
                               follow_redirects=True)
        self.assertIn('You are no longer following test2', resp.data)
        self.assertIn('Followers: 0', resp.data)
        # Check the list testing tag has gone
        self.assertNotIn('<!-- list:user:test1 -->', resp.data)

        # Attempt to unfollow the user again
        resp = self.client.get(url_for('unfollow', username='test2',
                               next=url_for('followers', username='test2')),
                               follow_redirects=True)
        self.assertNotIn('You are no longer following test2', resp.data)
        self.assertIn('Followers: 0', resp.data)

        # Ensure test2 is missing from YOUR (test1s) following page
        resp = self.client.get(url_for('following', username='test1'))
        self.assertNotIn('<!-- list:user:test2 -->', resp.data)
        # Done for now

    def test_search(self):
        """
        Ensure the search works and users are shown correctly.
        """
        # Let's try and access the endpoint feature when we are not logged in
        # We should not be able to see it
        resp = self.client.get('search', follow_redirects=True)
        self.assertIn('You need to be logged in to view that', resp.data)

        # We need some users with usernames different enough that we can test
        self.assertEqual(create_user('test1', 'test1@pjuu.com', 'Password'), 1)
        self.assertEqual(create_user('test2', 'test2@pjuu.com', 'Password'), 2)
        self.assertEqual(create_user('joe', 'joe@pjuu.com', 'Password'), 3)
        self.assertEqual(create_user('ant', 'ant@pjuu.com', 'Password'), 4)
        self.assertEqual(create_user('fil', 'fil@pjuu.com', 'Password'), 5)
        # Activate some of the accounts.
        self.assertTrue(activate(1))
        self.assertTrue(activate(2))
        self.assertTrue(activate(3))
        self.assertTrue(activate(4))

        # Let's sign in!
        # We will sign in as joe this time as that is me
        self.client.post('signin', data={
            'username': 'joe',
            'password': 'Password'
        })

        # Let's check we see the correct thing on the search page when there
        # is no search
        resp = self.client.get(url_for('search'))
        self.assertIn('<h1>Search for users</h1>', resp.data)
        self.assertNotIn('<h1>Results:', resp.data)

        # Lets search for ourselves
        resp = self.client.get(url_for('search', query='joe'))
        self.assertIn('<!-- list:user:joe -->', resp.data)

        # Lets check that this is case-insensitive
        resp = self.client.get(url_for('search', query='JOE'))
        self.assertIn('<!-- list:user:joe -->', resp.data)

        # Lets try this partially
        resp = self.client.get(url_for('search', query='j'))
        self.assertIn('<!-- list:user:joe -->', resp.data)

        # Lets check we see two users if two match
        resp = self.client.get(url_for('search', query='test'))
        self.assertIn('<!-- list:user:test1 -->', resp.data)
        self.assertIn('<!-- list:user:test2 -->', resp.data)

        # Lets check to see if inactive users show up. THEY SHOULD
        resp = self.client.get(url_for('search', query='fil'))
        self.assertIn('<!-- list:user:fil -->', resp.data)

        # Lets check that we can find ant because we are going to delete him
        # to ensure he goes! This has caused issues on the live site
        resp = self.client.get(url_for('search', query='ant'))
        self.assertIn('<!-- list:user:ant -->', resp.data)

        # We will just backend delete the account. Its this tests job to test
        # deletion
        delete_account(4)
        # Account is gone, lets ensure this has gone
        resp = self.client.get(url_for('search', query='ant'))
        self.assertNotIn('<!-- list:user:ant -->', resp.data)
        # Done for now!

    def test_settings_profile(self):
        """
        Ensure users have the ability to see some information about there
        account and can change there about message
        """
        # Let's try and access the endpoint feature when we are not logged in
        # We should not be able to see it
        resp = self.client.get('settings_profile', follow_redirects=True)
        self.assertIn('You need to be logged in to view that', resp.data)

        # Create a test user
        self.assertEqual(create_user('test1', 'test1@pjuu.com', 'Password'), 1)
        # Activate it
        self.assertTrue(activate(1))

        # Signin
        self.client.post(url_for('signin'), data={
            'username': 'test1',
            'password': 'Password'
        })

        # Go to our settings page and ensure everything is there
        resp = self.client.get(url_for('settings_profile'))
        self.assertIn('User Name: <b>test1</b>', resp.data)
        self.assertIn('E-mail address: <b>test1@pjuu.com</b>', resp.data)
        # Post to the form and update our about. We should also be this on
        # this page
        resp = self.client.post(url_for('settings_profile'), data={
            'about': 'Otters love fish!'
        }, follow_redirects=True)
        self.assertIn('Otters love fish!', resp.data)
        # Done for now

    def test_alerts(self):
        """
        Check that alerts are displayed properly in the frontend
        """
        # Create two test users
        user1 = create_user('test1', 'test1@pjuu.com', 'Password')
        user2 = create_user('test2', 'test2@pjuu.com', 'Password')
        # Activate
        activate(user1)
        activate(user2)

        # Login as user1
        resp = self.client.post(url_for('signin'), data={
            'username': 'test1',
            'password': 'Password'
        })

        # Get I has alerts and check that it is false
        resp = self.client.get(url_for('i_has_alerts'))
        # Check the JSON response
        self.assertFalse(json.loads(resp.data).get('result'))

        # Ensure that /alerts returns nothing
        resp = self.client.get(url_for('alerts'))
        self.assertNotIn('list:alert', resp.data)
        self.assertIn('Empty', resp.data)

        # Get user2 to follow user1
        follow_user(user2, user1)

        # Ensure that /i-has-alerts is correct
        resp = self.client.get(url_for('i_has_alerts'))
        # Check the JSON response
        self.assertTrue(json.loads(resp.data).get('result'))

        # Ensure that /alerts returns nothing
        resp = self.client.get(url_for('alerts'))
        self.assertIn('list:alert', resp.data)
        self.assertNotIn('Empty', resp.data)
        # Check test2's name is there
        self.assertIn('test2', resp.data)
        # Check that the prettify message from FollowAlert is there
        self.assertIn('has started following you', resp.data)

        # We have now checked the alerts, ensure that i-has-alerts is False
        resp = self.client.get(url_for('i_has_alerts'))
        # Check the JSON response
        self.assertFalse(json.loads(resp.data).get('result'))

        # Check that we can delete the alert
        # Get the alert id from the backend function
        aid = get_alerts(user1).items[0].aid

        resp = self.client.get(url_for('delete_alert', aid=aid),
                               follow_redirects=True)
        self.assertIn('Alert has been removed', resp.data)
        # Check that there are also no alerts now
        self.assertIn('Empty', resp.data)

        # Done for now
