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
        Tests for the 2 functions which are used on the side to get alerts and
        also test FollowAlert from here.
        """
        # Create 2 test users
        user1 = create_user('test1', 'test1@pjuu.com', 'Password')
        user2 = create_user('test2', 'test2@pjuu.com', 'Password')

        # Ensure that get_alerts pagination object is empty
        self.assertEqual(get_alerts(user1).total, 0)
        self.assertEqual(len(get_alerts(user1).items), 0)

        # Get user 2 to follow user 1
        follow_user(user2, user1)

        # Check that i_has_alerts is True
        self.assertTrue(i_has_alerts(user1))

        # Ensure that there is an alert in the get_alerts
        self.assertEqual(get_alerts(user1).total, 1)
        self.assertEqual(len(get_alerts(user1).items), 1)

        # Check that i_has_alerts is False, we have read them with get_alerts
        self.assertFalse(i_has_alerts(user1))

        # Get the alert and check that the alert is the follow alert
        alert = get_alerts(user1).items[0]
        self.assertTrue(isinstance(alert, FollowAlert))
        # Also check it's still a BaseAlert
        self.assertTrue(isinstance(alert, BaseAlert))
        # Check its from test2
        self.assertEqual(alert.get_username(), 'test2')
        self.assertEqual(alert.get_email(), 'test2@pjuu.com')
        self.assertIn('has started following you', alert.prettify())

        # Delete test2 and ensure we get no alerts
        delete_account(user2)

        # Ensure the alert is still inside Redis
        self.assertEqual(r.zcard(K.USER_ALERTS % user1), 1)

        # Get the alerts, should be none and should also clear the alert from
        # Redis
        self.assertEqual(get_alerts(user1).total, 0)
        self.assertEqual(len(get_alerts(user1).items), 0)
        self.assertEqual(r.zcard(K.USER_ALERTS % user1), 0)

        # Do the same as above to ensure we can delete an alert ourselves
        # Create user2 again as test3
        user2 = create_user('test3', 'test3@pjuu.com', 'Password')

        follow_user(user1, user2)

        # Check the alerts are there
        alert = get_alerts(user2).items[0]
        self.assertTrue(isinstance(alert, FollowAlert))
        # Also check it's still a BaseAlert
        self.assertTrue(isinstance(alert, BaseAlert))
        # Check its from test2
        self.assertEqual(alert.get_username(), 'test1')
        self.assertEqual(alert.get_email(), 'test1@pjuu.com')
        self.assertIn('has started following you', alert.prettify())

        # Delete the alert with aid from the alert
        delete_alert(user2, alert.aid)

        # Get the alerts and ensure the list is empty
        self.assertEqual(get_alerts(user2).total, 0)
        self.assertEqual(len(get_alerts(user2).items), 0)
        self.assertEqual(r.zcard(K.USER_ALERTS % user2), 0)

        # Done for now
