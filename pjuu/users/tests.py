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

# 3rd party imports
from flask import current_app as app, url_for, g
# Pjuu imports
from pjuu import redis as r
from pjuu.lib import keys as K
# We only need alert manage, the wonders of Pickling eh?
from pjuu.lib.alerts import AlertManager
from pjuu.lib.test_helpers import BackendTestCase, FrontendTestCase
from pjuu.auth.backend import create_user, delete_account, activate
from pjuu.posts.backend import (create_post, create_comment, TaggingAlert,
                                CommentingAlert)
from .backend import *


###############################################################################
# BACKEND #####################################################################
###############################################################################


class BackendTests(BackendTestCase):
    """
    This case will test ALL post backend functions.
    """

    def test_get_profile(self):
        """
        Tests that a user's profile representation can be returned
        """
        # Get test user
        self.assertEqual(create_user('test', 'test@pjuu.com', 'Password'), 1)
        # Attempt to get the users repr
        profile = get_profile(1)
        # Ensure we got a profile
        self.assertIsNotNone(profile)
        # Check all the keys are present
        self.assertEqual(profile['uid'], u'1')
        self.assertEqual(profile['username'], 'test')
        self.assertEqual(profile['email'], 'test@pjuu.com')
        # Ensure all the injected information is present
        self.assertEqual(profile['post_count'], 0)
        self.assertEqual(profile['followers_count'], 0)
        self.assertEqual(profile['following_count'], 0)
        # Ensure a non-existant profile return None
        self.assertEqual(get_profile(2), None)

    def test_get_user(self):
        """
        Tests that a user's account can be returned
        """
        # Get test user
        self.assertEqual(create_user('test', 'test@pjuu.com', 'Password'), 1)
        # Attempt to get the users repr
        user = get_user(1)
        # Ensure we got a profile
        self.assertIsNotNone(user)
        # Check all the keys are present
        self.assertEqual(user['uid'], u'1')
        self.assertEqual(user['username'], 'test')
        self.assertEqual(user['email'], 'test@pjuu.com')
        # Ensure a non-existant user return None
        self.assertEqual(get_user(2), None)

    def test_get_feed(self):
        """
        Attempt to get a users feed under certain circumstances.
        """
        # Get test user
        self.assertEqual(create_user('test1', 'test1@pjuu.com', 'Password'), 1)
        # Ensure an empty feed is returned. Remember these are paginations
        self.assertEqual(len(get_feed(1).items), 0)
        # Ensure a users own post is added to thier feed
        self.assertEqual(create_post(1, 'Test post'), 1)
        # Ensure the list is the correct length
        self.assertEqual(len(get_feed(1).items), 1)
        self.assertEqual(get_feed(1).total, 1)
        # Ensure the item is in Redis
        self.assertIn('1', r.lrange(K.USER_FEED % 1, 0, -1))
        # Create a second user, make 1 follow them, make then post and ensure
        # that the new users post appears in user 1s feed
        self.assertEqual(create_user('test2', 'test2@pjuu.com', 'Password'), 2)
        self.assertTrue(follow_user(1, 2))
        self.assertEqual(create_post(2, 'Test post'), 2)
        # Check user 1's feed for the next item
        self.assertEqual(len(get_feed(1).items), 2)
        self.assertEqual(get_feed(1).total, 2)
        # Ensure the item is in Redis
        self.assertIn('2', r.lrange(K.USER_FEED % 1, 0, -1))
        # Delete user 2 and ensure user 1's feed cleans itself
        delete_account(2)
        self.assertEqual(len(get_feed(1).items), 1)
        self.assertEqual(get_feed(1).total, 1)
        # Ensure the item is in Redis
        self.assertNotIn('2', r.lrange(K.USER_FEED % 1, 0, -1))

    def test_get_posts(self):
        """
        Test users post list works correctly
        """
        # Create test user
        self.assertEqual(create_user('test', 'test@pjuu.com', 'Password'), 1)
        # Ensure the users post list is empty
        self.assertEqual(len(get_posts(1).items), 0)
        # Create a test post, ensure it appears in the users list
        self.assertEqual(create_post(1, 'Test post'), 1)
        self.assertEqual(len(get_posts(1).items), 1)
        self.assertEqual(get_posts(1).total, 1)
        # Ensure the post id is in the Redis list
        self.assertIn('1', r.lrange(K.USER_POSTS % 1, 0, -1))
        # Done

    def test_get_comments(self):
        """
        Ensure a posts comments are stored correctly in post:$pid:comments list
        """
        # Create two test users
        self.assertEqual(create_user('test1', 'test1@pjuu.com', 'Password'), 1)
        self.assertEqual(create_user('test2', 'test2@pjuu.com', 'Password'), 2)
        # Ensure the comment lists are empty
        self.assertEqual(len(get_comments(1).items), 0)
        self.assertEqual(len(get_comments(2).items), 0)
        # Create a post for each user and a comment on each for both user
        self.assertEqual(create_post(1, 'Test post'), 1)
        self.assertEqual(create_post(2, 'Test post'), 2)
        self.assertEqual(create_comment(1, 1, 'Test comment'), 1)
        self.assertEqual(create_comment(1, 2, 'Test comment'), 2)
        self.assertEqual(create_comment(2, 1, 'Test comment'), 3)
        self.assertEqual(create_comment(2, 2, 'Test comment'), 4)
        # Ensure each comment appears in each users list
        self.assertEqual(len(get_comments(1).items), 2)
        self.assertEqual(len(get_comments(2).items), 2)
        # Ensure the totals are correct
        self.assertEqual(get_comments(1).total, 2)
        self.assertEqual(get_comments(2).total, 2)
        # Ensure the ids are in the Redis lists
        self.assertIn('1', r.lrange(K.USER_COMMENTS % 1, 0, -1))
        self.assertIn('2', r.lrange(K.USER_COMMENTS % 1, 0, -1))
        self.assertIn('3', r.lrange(K.USER_COMMENTS % 2, 0, -1))
        self.assertIn('4', r.lrange(K.USER_COMMENTS % 2, 0, -1))
        # Done

    def test_follow_unfollow_get_followers_following_is_following(self):
        """
        Test everything about following. There is not that much to it to
        deserve 3 seperate methods.
        """
        # Create two test users
        self.assertEqual(create_user('test1', 'test1@pjuu.com', 'Password'), 1)
        self.assertEqual(create_user('test2', 'test2@pjuu.com', 'Password'), 2)
        # Ensure is_following() is false atm
        self.assertFalse(is_following(1, 2))
        self.assertFalse(is_following(2, 1))
        # Ensure user 1 can follow user 2
        self.assertTrue(follow_user(1, 2))
        # Ensure the user can't follow them again
        self.assertFalse(follow_user(1, 2))
        # And visa-versa
        self.assertTrue(follow_user(2, 1))
        # Ensre the user can't follow them again
        self.assertFalse(follow_user(2, 1))
        # Ensure the id's are in the Redis sorted sets, followers and following
        self.assertIn('2', r.zrange(K.USER_FOLLOWING % 1, 0, -1))
        self.assertIn('2', r.zrange(K.USER_FOLLOWERS % 1, 0, -1))
        self.assertIn('1', r.zrange(K.USER_FOLLOWING % 2, 0, -1))
        self.assertIn('1', r.zrange(K.USER_FOLLOWERS % 2, 0, -1))
        # Ensure the get_followers and get_following functions return
        # the correct data
        self.assertEqual(len(get_following(1).items), 1)
        self.assertEqual(len(get_following(1).items), 1)
        self.assertEqual(len(get_following(2).items), 1)
        self.assertEqual(len(get_following(2).items), 1)
        # Ensure the totals are correct
        self.assertEqual(get_following(1).total, 1)
        self.assertEqual(get_followers(1).total, 1)
        self.assertEqual(get_following(2).total, 1)
        self.assertEqual(get_followers(1).total, 1)
        # Make sure is_following() returns correctly
        self.assertTrue(is_following(1, 2))
        self.assertTrue(is_following(2, 1))
        # User 1 unfollow user 2 and ensure the sorted sets are updated
        self.assertTrue(unfollow_user(1, 2))
        self.assertNotIn('2', r.zrange(K.USER_FOLLOWING % 1, 0, -1))
        self.assertNotIn('1', r.zrange(K.USER_FOLLOWERS % 2, 0, -1))
        # Ensure the user can't unfollow the user again
        self.assertFalse(unfollow_user(1, 2))
        # User 2 unfollow user 1 and ensure the sorted sets are updates
        self.assertTrue(unfollow_user(2, 1))
        self.assertNotIn('1', r.zrange(K.USER_FOLLOWING % 2, 0, -1))
        self.assertNotIn('2', r.zrange(K.USER_FOLLOWERS % 1, 0, -1))
        # Let's make sure unfollow won't work... AGAIN
        self.assertFalse(unfollow_user(2, 1))
        # Ensure get_followers and get_following return the correct value
        self.assertEqual(len(get_following(1).items), 0)
        self.assertEqual(len(get_following(1).items), 0)
        self.assertEqual(len(get_following(2).items), 0)
        self.assertEqual(len(get_following(2).items), 0)
        # Ensure the totals are correct
        self.assertEqual(get_following(1).total, 0)
        self.assertEqual(get_followers(1).total, 0)
        self.assertEqual(get_following(2).total, 0)
        self.assertEqual(get_followers(1).total, 0)
        # Make sure is_following() returns correctly
        self.assertFalse(is_following(1, 2))
        self.assertFalse(is_following(2, 1))
        # Done

    def test_search(self):
        """
        Make sure users can actually find each other.

        This will need a lot more work once we add in a proper search facility
        rather than just the Redis KEYS command
        """
        # Create test user
        self.assertEqual(create_user('test1', 'test1@pjuu.com', 'Password'), 1)
        # Ensure that the user can be found
        self.assertEqual(len(search('test1').items), 1)
        self.assertEqual(search('test1').total, 1)
        # Ensure partial match
        self.assertEqual(len(search('tes').items), 1)
        self.assertEqual(search('tes').total, 1)
        # Ensure nothing return if no user
        self.assertEqual(len(search('test2').items), 0)
        self.assertEqual(search('test2').total, 0)
        # Ensure no partial if incorrect
        self.assertEqual(len(search('bob').items), 0)
        self.assertEqual(search('bob').total, 0)
        # Create a second test user
        self.assertEqual(create_user('test2', 'test2@pjuu.com', 'Password'), 2)
        # Ensure the new user can be found
        self.assertEqual(len(search('test2').items), 1)
        self.assertEqual(search('test2').total, 1)
        # Ensure partial match returns both test1/2 users
        self.assertEqual(len(search('tes').items), 2)
        self.assertEqual(search('tes').total, 2)
        # Delete the account test 2 and try searching again
        # Adding in this test as it has stung us before
        self.assertIsNone(delete_account(2))
        self.assertEqual(search('test2').total, 0)
        # Done

    def test_alerts(self):
        """
        This will test many of the alert features.

        Note: This is also going to test the current alerts being created by
              the posts app as Alerts is a lib/users thing.

              If you add new alerts in future an would like to test them I
              suggest you do it HERE and maybe add a line to test_alerts in
              FrontendTests.test_alerts also.

              Also note that although the alerts system in posts relies on
              the subscription system, subscriptions are solely a posts things
              and as such are tested there.
        """
        # Create 2 users and have them follow each other
        self.assertEqual(create_user('test1', 'test1@pjuu.com', 'Password'), 1)
        self.assertEqual(create_user('test2', 'test2@pjuu.com', 'Password'), 2)
        self.assertTrue(activate(1))
        self.assertTrue(activate(2))

        # Check the users alerts zset does not exist
        self.assertFalse(r.exists(K.USER_ALERTS % 1))
        self.assertFalse(r.exists(K.USER_ALERTS % 2))

        # Get the users to follow each other this can be our first test
        # of the alerts system as these are alerted on :D
        self.assertTrue(follow_user(1, 2))
        self.assertTrue(follow_user(2, 1))

        # Assert the alerts zset exist and does as we expect
        self.assertTrue(r.exists(K.USER_ALERTS % 1))
        self.assertTrue(r.exists(K.USER_ALERTS % 2))
        # Assert the length (ZCARD) of each is one
        self.assertEqual(r.zcard(K.USER_ALERTS % 1), 1)
        self.assertEqual(r.zcard(K.USER_ALERTS % 2), 1)

        # Get one of the alerts are doing check the correct uid is set
        # Just pull the first item from the zset thats probably easiest
        alert_pickle = r.zrevrange(K.USER_ALERTS % 1, 0, 0)[0]
        # Let's get an alert manager
        am = AlertManager()
        am.loads(alert_pickle)

        # Check that is user two who created the alert
        self.assertEqual(am.alert.uid, 2)
        # Check that prettify include user2's username and not mine
        self.assertIn('test2', am.alert.prettify())
        self.assertNotIn('test1', am.alert.prettify())
        # Assert part of the prettify word is there
        self.assertIn('has started following you', am.alert.prettify())
        self.assertEqual(type(am.alert), FollowAlert)

        # This is a FollowAlert, ensure it does not have a pid
        self.assertFalse(hasattr(am.alert, 'pid'))

        # We are not getting in to the realm of tagging each other.
        # Yes, yes, posts code, but let do this properly
        self.assertEqual(create_post(1, 'Hello @test2'), 1)

        # Lets check test2's alerts zset again an ensure it has grown
        self.assertEqual(r.zcard(K.USER_ALERTS % 2), 2)

        # Get the second alert and double check a few things
        alert_pickle = r.zrevrange(K.USER_ALERTS % 2, 0, 0)[0]
        # Let's get an alert manager
        am = AlertManager()
        am.loads(alert_pickle)

        # Check additional data
        self.assertEqual(am.alert.uid, 1)
        # Don't check for pid, just get it, it should be there
        self.assertEqual(am.alert.pid, 1)
        self.assertEqual(am.alert.get_username(), 'test1')
        self.assertEqual(am.alert.get_email(), 'test1@pjuu.com')
        self.assertIn(' tagged you in a ', am.alert.prettify())
        self.assertEqual(type(am.alert), TaggingAlert)

        # Get test2 to comment on the post, it should alert test1 but not test2
        self.assertEqual(create_comment(2, 1, 'Hello friend'), 1)
        # Check the length of both users alerts zset's
        # User 1 should now be equal with 2 alerts
        self.assertEqual(r.zcard(K.USER_ALERTS % 1), 2)
        self.assertEqual(r.zcard(K.USER_ALERTS % 2), 2)

        # Get the new alert from test1 and ensure they are post correct
        alert_pickle = r.zrevrange(K.USER_ALERTS % 1, 0, 0)[0]
        # Let's get an alert manager
        am = AlertManager()
        am.loads(alert_pickle)

        # Check the data
        self.assertEqual(am.alert.uid, 2)
        self.assertEqual(am.alert.pid, 1)
        self.assertEqual(am.alert.get_username(), 'test2')
        self.assertEqual(am.alert.get_email(), 'test2@pjuu.com')
        self.assertEqual(type(am.alert), CommentingAlert)
        # This is a sort of test of the subscription system.
        # I should be being alerted because I was originally tagged
        # Let's check that from prettify
        self.assertIn('you posted', am.alert.prettify())

        # Create a post as test1
        self.assertEqual(create_post(1, 'Hello again'), 2)
        # Create a comment as test1 and tag test2 in the comment
        self.assertEqual(create_comment(1, 2, 'Oh and @test2'), 2)

        # Get test2's alert feed and ensure that this alert is there
        alert_pickle = r.zrevrange(K.USER_ALERTS % 2, 0, 0)[0]
        # Let's get an alert manager
        am = AlertManager()
        am.loads(alert_pickle)

        # Check the data
        self.assertEqual(am.alert.uid, 1) # Ensure test1
        self.assertEqual(am.alert.pid, 2)
        self.assertEqual(am.alert.get_username(), 'test1')
        self.assertEqual(am.alert.get_email(), 'test1@pjuu.com')
        self.assertEqual(type(am.alert), TaggingAlert)

        # Done for the present moment


###############################################################################
# FRONTEND ####################################################################
###############################################################################


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
