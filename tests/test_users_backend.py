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
from pjuu.posts.backend import (create_post, create_comment, delete_post,
                                delete_comment, TaggingAlert, CommentingAlert)
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
        user1 = create_user('user1', 'user1@pjuu.com', 'Password')
        # Attempt to get the users repr
        profile = get_profile(user1)
        # Ensure we got a profile
        self.assertIsNotNone(profile)

        # Check all the keys are present
        self.assertEqual(profile.get('uid'), user1)
        self.assertEqual(profile.get('username'), 'user1')
        self.assertEqual(profile.get('email'), 'user1@pjuu.com')
        # Ensure all the injected information is present
        self.assertEqual(profile.get('post_count'), 0)
        self.assertEqual(profile.get('followers_count'), 0)
        self.assertEqual(profile.get('following_count'), 0)

        # Ensure a non-existant profile return None
        self.assertEqual(get_profile(K.NIL_VALUE), None)

    def test_get_user(self):
        """
        Tests that a user's account can be returned
        """
        # Get test user
        user1 = create_user('user1', 'user1@pjuu.com', 'Password')
        # Attempt to get the users repr
        user = get_user(user1)
        # Ensure we got a profile
        self.assertIsNotNone(user)
        # Check all the keys are present
        self.assertEqual(user.get('uid'), user1)
        self.assertEqual(user.get('username'), 'user1')
        self.assertEqual(user.get('email'), 'user1@pjuu.com')
        # Ensure a non-existant user return None
        self.assertEqual(get_user(K.NIL_VALUE), None)

    def test_get_feed(self):
        """
        Attempt to get a users feed under certain circumstances.
        """
        # Get test user
        user1 = create_user('user1', 'user1@pjuu.com', 'Password')
        # Ensure an empty feed is returned. Remember these are paginations
        self.assertEqual(len(get_feed(user1).items), 0)
        # Ensure a users own post is added to thier feed
        post1 = create_post(user1, 'Test post')
        # Ensure the list is the correct length
        self.assertEqual(len(get_feed(user1).items), 1)
        self.assertEqual(get_feed(user1).total, 1)
        # Ensure the item is in Redis
        self.assertIn(post1, r.lrange(K.USER_FEED.format(user1), 0, -1))

        # Create a second user, make 1 follow them, make then post and ensure
        # that the new users post appears in user 1s feed
        user2 = create_user('user2', 'user2@pjuu.com', 'Password')
        follow_user(user1, user2)

        post2 = create_post(user2, 'Test post')
        # Check user 1's feed for the next item
        self.assertEqual(len(get_feed(user1).items), 2)
        self.assertEqual(get_feed(user1).total, 2)
        # Ensure the item is in Redis
        self.assertIn(post2, r.lrange(K.USER_FEED.format(user1), 0, -1))
        # Delete user 2 and ensure user 1's feed cleans itself
        delete_account(user2)
        self.assertEqual(len(get_feed(user1).items), 1)
        self.assertEqual(get_feed(user1).total, 1)
        # Ensure the item is not in Redis
        self.assertNotIn(post2, r.lrange(K.USER_FEED.format(user1), 0, -1))

    def test_get_posts(self):
        """
        Test users post list works correctly
        """
        # Create test user
        user1 = create_user('user1', 'user1@pjuu.com', 'Password')
        # Ensure the users post list is empty
        self.assertEqual(len(get_posts(user1).items), 0)

        # Create a few test posts, ensure they appears in the users list
        post1 = create_post(user1, 'Test post 1')
        post2 = create_post(user1, 'Test post 2')
        post3 = create_post(user1, 'Test post 3')
        self.assertEqual(len(get_posts(user1).items), 3)
        self.assertEqual(get_posts(user1).total, 3)

        # Ensure the post ids are in the Redis list
        self.assertIn(post1, r.lrange(K.USER_POSTS.format(user1), 0, -1))
        self.assertIn(post2, r.lrange(K.USER_POSTS.format(user1), 0, -1))
        self.assertIn(post3, r.lrange(K.USER_POSTS.format(user1), 0, -1))

        # Delete one of the posts and ensure that it does not appear in the
        # list.
        delete_post(post1)

        # Ensure the above is now correct with post1 missing
        self.assertEqual(len(get_posts(user1).items), 2)
        self.assertEqual(get_posts(user1).total, 2)

        # Ensure the post ids are in the Redis list and post1 is NOT
        self.assertNotIn(post1, r.lrange(K.USER_POSTS.format(user1), 0, -1))
        self.assertIn(post2, r.lrange(K.USER_POSTS.format(user1), 0, -1))
        self.assertIn(post3, r.lrange(K.USER_POSTS.format(user1), 0, -1))

        # Delete a post from inside Redis. This will trigger the self cleaning
        # list feature. We call these orphaned pids
        r.delete(K.POST.format(post2))
        # Ensure the above is now correct with post2 missing
        self.assertEqual(len(get_posts(user1).items), 1)
        self.assertEqual(get_posts(user1).total, 1)

        # Ensure the post ids are not in the Redis list and post1 is NOT
        self.assertNotIn(post1, r.lrange(K.USER_POSTS.format(user1), 0, -1))
        self.assertNotIn(post2, r.lrange(K.USER_POSTS.format(user1), 0, -1))
        self.assertIn(post3, r.lrange(K.USER_POSTS.format(user1), 0, -1))

        # Done

    def test_get_comments(self):
        """
        Ensure a posts comments are stored correctly in post:$pid:comments list
        """
        # Create two test users
        user1 = create_user('user1', 'user1@pjuu.com', 'Password')
        user2 = create_user('user2', 'user2@pjuu.com', 'Password')
        # Ensure the comment lists are empty
        self.assertEqual(len(get_comments(user1).items), 0)
        self.assertEqual(len(get_comments(user2).items), 0)
        # Create a post for each user and a comment on each for both user
        post1 = create_post(user1, 'Test post')
        post2 = create_post(user2, 'Test post')
        comment1 = create_comment(user1, post1, 'Test comment')
        comment2 = create_comment(user1, post2, 'Test comment')
        comment3 = create_comment(user2, post1, 'Test comment')
        comment4 = create_comment(user2, post2, 'Test comment')
        # Ensure each comment appears in each users list
        self.assertEqual(len(get_comments(post1).items), 2)
        self.assertEqual(len(get_comments(post2).items), 2)
        # Ensure the totals are correct
        self.assertEqual(get_comments(post1).total, 2)
        self.assertEqual(get_comments(post2).total, 2)
        # Ensure the ids are in the Redis lists
        self.assertIn(comment1, r.lrange(K.POST_COMMENTS.format(post1), 0, -1))
        self.assertIn(comment2, r.lrange(K.POST_COMMENTS.format(post2), 0, -1))
        self.assertIn(comment3, r.lrange(K.POST_COMMENTS.format(post1), 0, -1))
        self.assertIn(comment4, r.lrange(K.POST_COMMENTS.format(post2), 0, -1))

        # Delete 1 comment from post1 and ensure it does not exist
        delete_comment(comment1)
        # Check that is has gone
        self.assertEqual(len(get_comments(post1).items), 1)
        self.assertEqual(get_comments(post1).total, 1)
        # Ensure it is missing from Redis
        self.assertNotIn(comment1,
                         r.lrange(K.POST_COMMENTS.format(user1), 0, -1))

        # Delete a comment from inside Redis. This will trigger the self
        # cleaning list feature. We call these orphaned cids.
        r.delete(K.COMMENT.format(comment2))
        # Check that it has gone when get_comments is called
        self.assertEqual(len(get_comments(post2).items), 1)
        self.assertEqual(get_comments(post2).total, 1)
        # Ensure it is missing from Redis
        self.assertNotIn(comment2,
                         r.lrange(K.POST_COMMENTS.format(user1), 0, -1))

    def test_follow_unfollow_get_followers_following_is_following(self):
        """
        Test everything about following. There is not that much to it to
        deserve 3 seperate methods.
        """
        # Create two test users
        user1 = create_user('user1', 'user1@pjuu.com', 'Password')
        user2 = create_user('user2', 'user2@pjuu.com', 'Password')
        # Ensure is_following() is false atm
        self.assertFalse(is_following(user1, user2))
        self.assertFalse(is_following(user2, user1))
        # Ensure user 1 can follow user 2
        self.assertTrue(follow_user(user1, user2))
        # Ensure the user can't follow them again
        self.assertFalse(follow_user(user1, user2))
        # And visa-versa
        self.assertTrue(follow_user(user2, user1))
        # Ensre the user can't follow them again
        self.assertFalse(follow_user(user2, user1))
        # Ensure the id's are in the Redis sorted sets, followers and following
        self.assertIn(user2, r.zrange(K.USER_FOLLOWING.format(user1), 0, -1))
        self.assertIn(user2, r.zrange(K.USER_FOLLOWERS.format(user1), 0, -1))
        self.assertIn(user1, r.zrange(K.USER_FOLLOWING.format(user2), 0, -1))
        self.assertIn(user1, r.zrange(K.USER_FOLLOWERS.format(user2), 0, -1))
        # Ensure the get_followers and get_following functions return
        # the correct data
        self.assertEqual(len(get_following(user1).items), 1)
        self.assertEqual(len(get_following(user1).items), 1)
        self.assertEqual(len(get_following(user2).items), 1)
        self.assertEqual(len(get_following(user2).items), 1)
        # Ensure the totals are correct
        self.assertEqual(get_following(user1).total, 1)
        self.assertEqual(get_followers(user1).total, 1)
        self.assertEqual(get_following(user2).total, 1)
        self.assertEqual(get_followers(user2).total, 1)
        # Make sure is_following() returns correctly
        self.assertTrue(is_following(user1, user2))
        self.assertTrue(is_following(user2, user1))
        # User 1 unfollow user 2 and ensure the sorted sets are updated
        self.assertTrue(unfollow_user(user1, user2))
        self.assertNotIn(user2,
                         r.zrange(K.USER_FOLLOWING.format(user1), 0, -1))
        self.assertNotIn(user1,
                         r.zrange(K.USER_FOLLOWERS.format(user2), 0, -1))
        # Ensure the user can't unfollow the user again
        self.assertFalse(unfollow_user(user1, user2))
        # User 2 unfollow user 1 and ensure the sorted sets are updates
        self.assertTrue(unfollow_user(user2, user1))
        self.assertNotIn(user1,
                         r.zrange(K.USER_FOLLOWING.format(user2), 0, -1))
        self.assertNotIn(user2,
                         r.zrange(K.USER_FOLLOWERS.format(user1), 0, -1))
        # Let's make sure unfollow won't work... AGAIN
        self.assertFalse(unfollow_user(user2, user1))
        # Ensure get_followers and get_following return the correct value
        self.assertEqual(len(get_following(user1).items), 0)
        self.assertEqual(len(get_following(user1).items), 0)
        self.assertEqual(len(get_following(user2).items), 0)
        self.assertEqual(len(get_following(user2).items), 0)
        # Ensure the totals are correct
        self.assertEqual(get_following(user1).total, 0)
        self.assertEqual(get_followers(user1).total, 0)
        self.assertEqual(get_following(user2).total, 0)
        self.assertEqual(get_followers(user2).total, 0)
        # Make sure is_following() returns correctly
        self.assertFalse(is_following(user1, user2))
        self.assertFalse(is_following(user2, user1))
        # Done

    def test_search(self):
        """
        Make sure users can actually find each other.

        This will need a lot more work once we add in a proper search facility
        rather than just the Redis KEYS command
        """
        # Create test user
        user1 = create_user('user1', 'user1@pjuu.com', 'Password')
        # Ensure that the user can be found
        self.assertEqual(len(search('user1').items), 1)
        self.assertEqual(search('user1').total, 1)
        # Ensure partial match
        self.assertEqual(len(search('use').items), 1)
        self.assertEqual(search('use').total, 1)
        # Ensure nothing return if no user
        self.assertEqual(len(search('user2').items), 0)
        self.assertEqual(search('user2').total, 0)
        # Ensure no partial if incorrect
        self.assertEqual(len(search('bob').items), 0)
        self.assertEqual(search('bob').total, 0)

        # Create a second test user
        user2 = create_user('user2', 'user2@pjuu.com', 'Password')
        # Ensure the new user can be found
        self.assertEqual(len(search('user2').items), 1)
        self.assertEqual(search('user2').total, 1)
        # Ensure partial match returns both test1/2 users
        self.assertEqual(len(search('use').items), 2)
        self.assertEqual(search('use').total, 2)

        # Delete the account test 2 and try searching again
        # Adding in this test as it has stung us before
        delete_account(user2)
        self.assertEqual(search('test2').total, 0)
        # Done

    def test_alerts(self):
        """
        Tests for the 2 functions which are used on the side to get alerts and
        also test FollowAlert from here.
        """
        # Create 2 test users
        user1 = create_user('user1', 'user1@pjuu.com', 'Password')
        user2 = create_user('user2', 'user2@pjuu.com', 'Password')

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
        self.assertEqual(alert.get_username(), 'user2')
        self.assertEqual(alert.get_email(), 'user2@pjuu.com')
        self.assertIn('has started following you', alert.prettify())

        # Delete test2 and ensure we get no alerts
        delete_account(user2)

        # Ensure the alert is still inside Redis
        self.assertEqual(r.zcard(K.USER_ALERTS.format(user1)), 1)

        # Get the alerts, should be none and should also clear the alert from
        # Redis
        self.assertEqual(get_alerts(user1).total, 0)
        self.assertEqual(len(get_alerts(user1).items), 0)
        self.assertEqual(r.zcard(K.USER_ALERTS.format(user1)), 0)

        # Do the same as above to ensure we can delete an alert ourselves
        # Create another user
        user3 = create_user('user3', 'user3@pjuu.com', 'Password')

        follow_user(user1, user3)

        # Check the alerts are there
        alert = get_alerts(user3).items[0]
        self.assertTrue(isinstance(alert, FollowAlert))
        # Also check it's still a BaseAlert
        self.assertTrue(isinstance(alert, BaseAlert))
        # Check its from test2
        self.assertEqual(alert.get_username(), 'user1')
        self.assertEqual(alert.get_email(), 'user1@pjuu.com')
        self.assertIn('has started following you', alert.prettify())

        # Delete the alert with aid from the alert
        delete_alert(user3, alert.aid)

        # Get the alerts and ensure the list is empty
        self.assertEqual(get_alerts(user3).total, 0)
        self.assertEqual(len(get_alerts(user3).items), 0)
        self.assertEqual(r.zcard(K.USER_ALERTS.format(user3)), 0)

        # Done for now
