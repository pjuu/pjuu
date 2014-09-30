# -*- coding: utf8 -*-

"""
Description:
    Posts package unit tests

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
from pjuu.auth.backend import create_user, activate, get_user, mute
from pjuu.lib import keys as K
from pjuu.posts.backend import *
from pjuu.users.backend import follow_user, get_alerts
# Tests imports
from tests.helpers import BackendTestCase, FrontendTestCase


class BackendTests(BackendTestCase):
    """
    This case will test ALL post backend functions.
    """

    def test_create_post(self):
        """
        Tests creating a post
        """
        # Create a user to test creating post
        self.assertEqual(create_user('test', 'test@pjuu.com', 'Password'), 1)
        # Create post
        self.assertEqual(create_post(1, 'Test post'), 1)
        # Check the post was created by looking at the pid
        self.assertEqual(int(get_post(1).get('pid', None)), 1)
        # Ensure the post gets added to the users 'posts' list
        # Remember redis returns everything as a string
        self.assertIn(u'1', r.lrange(K.USER_POSTS % 1, 0, -1))
        # Ensure this post is the users feed (populate_feed)
        self.assertIn(u'1', r.lrange(K.USER_FEED % 1, 0, -1))

    def test_create_comment(self):
        """
        Tests that a comment can be created on a post
        """
        self.assertEqual(create_user('test1', 'test1@pjuu.com', 'Password'), 1)
        # Create a second test user to test commenting on someone else post
        self.assertEqual(create_user('test2', 'test2@pjuu.com', 'Password'), 2)
        # Create post
        self.assertEqual(create_post(1, 'Test post'), 1)
        # Create comment
        self.assertEqual(create_comment(1, 1, 'Test comment'), 1)
        # Check the comment was created
        self.assertEqual(int(get_comment(1).get('cid', None)), 1)
        # Create a comment by the second user
        self.assertEqual(create_comment(2, 1, 'Test comment'), 2)
        # Check the comment was created
        self.assertEqual(int(get_comment(2).get('cid', None)), 2)
        # Ensure the comment is the posts 'comment' list
        # Remember redis returns everything as a string
        # This will fail if decode response is not enabled
        self.assertIn(u'1', r.lrange(K.POST_COMMENTS % 1, 0, -1))
        # Ensure the comment is also in the users 'comments' list
        self.assertIn(u'1', r.lrange(K.USER_COMMENTS % 1, 0, -1))
        # Ensure the same applies for the second users post
        self.assertIn(u'2', r.lrange(K.POST_COMMENTS % 1, 0, -1))
        # Ensure the comment is also in the users 'comments' list
        self.assertIn(u'2', r.lrange(K.USER_COMMENTS % 2, 0, -1))

    def test_check_post(self):
        """
        Will test that check_post returns the correct value with various
        combinations.

        Note: Bare with this one it is quite tedious.
        """
        # Create two test users
        self.assertEqual(create_user('test1', 'test1@pjuu.com', 'Password'), 1)
        self.assertEqual(create_user('test2', 'test2@pjuu.com', 'Password'), 2)
        # Create a post
        self.assertEqual(create_post(1, 'Test post'), 1)
        # check_post should be True when user 1 creates post 1
        self.assertTrue(check_post(1, 1))
        # check_post should be false, user 2 didn't create post 1
        self.assertFalse(check_post(2, 1))
        # Create a couple of comments
        self.assertEqual(create_comment(1, 1, 'Test comment'), 1)
        self.assertEqual(create_comment(2, 1, 'Test comment'), 2)
        # Ensure the check_post is fine for all
        self.assertTrue(check_post(1, 1, 1))
        # This does not look correct but is. See backend.py@check_post
        self.assertTrue(check_post(1, 1, 2))
        # Ensure the function isn't broken on comments
        self.assertFalse(check_post(2, 1, 1))
        self.assertFalse(check_post(1, 2, 1))
        self.assertFalse(check_post(2, 2, 2))

    def test_get_post_get_comment(self):
        """
        Will test that the get_post() and get_comment() functions of the posts
        system.

        These should return a representation of the post/comment including all
        the data needed to display these on the site. If they can not build
        this repr then they should return None. This will allow the lists to
        clean them selves when they encounter this.
        """
        # Create test user
        self.assertEqual(create_user('test', 'test@pjuu.com', 'Password'), 1)
        # Create test post
        self.assertEqual(create_post(1, 'Test post'), 1)
        # Attempt to get the repesentation
        post = get_post(1)
        self.assertIsNotNone(post)
        # Check the representation has all the correct fields
        self.assertEqual(post['uid'], '1')
        self.assertEqual(post['pid'], '1')
        self.assertEqual(post['body'], 'Test post')
        self.assertEqual(post['score'], '0')
        self.assertEqual(post['user_username'], 'test')
        self.assertEqual(post['user_email'], 'test@pjuu.com')
        self.assertEqual(post['comment_count'], 0)
        # Attempt to get a non existant post
        self.assertIsNone(get_post(2))
        # Attempt to get a post but one where the user is deleted.
        self.assertEqual(create_post(2, 'Test post'), 2)
        # Attempt to get the repesentation
        post = get_post(2)
        self.assertIsNone(post)

        # Create a comment and ensure the repr is updated and that we can
        # Get a comment repr
        self.assertEqual(create_comment(1, 1, 'Test comment'), 1)
        # Attempt to get the repesentation
        post = get_post(1)
        self.assertIsNotNone(post)
        # Check the comment count for the post
        self.assertEqual(post['comment_count'], 1)

        # Lets start testing comments, we will use the one above
        comment = get_comment(1)
        self.assertEqual(comment['uid'], '1')
        self.assertEqual(comment['pid'], '1')
        self.assertEqual(comment['cid'], '1')
        self.assertEqual(comment['body'], 'Test comment')
        self.assertEqual(comment['score'], '0')
        self.assertEqual(comment['user_username'], 'test')
        self.assertEqual(comment['user_email'], 'test@pjuu.com')
        # Attempt to get the post author. Remember this is a username as the
        # only use for it is to generate a URL /<username>/<pid>/<cid>/*
        self.assertEqual(comment['post_author'], 'test')
        # Attempt to get a non existant comment
        self.assertIsNone(get_comment(2))
        # Attempt to get a comment where the user is deleted
        self.assertEqual(create_comment(2, 1, 'Test comment'), 2)
        # Attempt to get the representation
        comment = get_comment(2)
        self.assertIsNone(comment)

    def test_votes(self):
        """
        Test that the voting mechanism will adjust the relevant score counters
        on users, posts and comments, etc...
        """
        # Create three test users
        self.assertEqual(create_user('test1', 'test1@pjuu.com', 'Password'), 1)
        self.assertEqual(create_user('test2', 'test2@pjuu.com', 'Password'), 2)
        self.assertEqual(create_user('test3', 'test3@pjuu.com', 'Password'), 3)
        # Create a post by user 1
        self.assertEqual(create_post(1, 'Test post'), 1)

        # Get user 3 to downvote, this will test that the user can not go
        # negative yet the post can
        self.assertTrue(vote(3, 1, amount=-1))
        # Ensure post score has been adjusted
        self.assertEqual(get_post(1)['score'], '-1')
        # Ensure user score has been adjusted
        self.assertEqual(get_user(1)['score'], '0')

        # Get user 2 to upvote
        self.assertTrue(vote(2, 1))
        # Ensure post score has been adjusted
        self.assertEqual(get_post(1)['score'], '0')
        # Ensure user score has been adjusted
        self.assertEqual(get_user(1)['score'], '1')
        # Ensure user 1 can not vote on there own comment
        self.assertFalse(vote(1, 1))
        # Ensure the score didn't adjust (may be a code bug some day)
        # Ensure post score has been adjusted
        self.assertEqual(get_post(1)['score'], '0')
        # Ensure user score has been adjusted
        self.assertEqual(get_user(1)['score'], '1')
        # Check to see if a user can vote twice on a comment
        self.assertFalse(vote(2, 1))
        # Ensure the score didn't adjust (may be a code bug some day)
        # Ensure post score has been adjusted
        self.assertEqual(get_post(1)['score'], '0')
        # Ensure user score has been adjusted
        self.assertEqual(get_user(1)['score'], '1')

        # Repeat the same tests on a comment
        # Create a comment by user 1
        self.assertEqual(create_comment(1, 1, 'Test comment'), 1)

        # Get user 3 to downvote
        self.assertTrue(vote(3, 1, 1, amount=-1))
        # Ensure post score has been adjusted
        self.assertEqual(get_comment(1)['score'], '-1')
        # Ensure user score has been adjusted
        self.assertEqual(get_user(1)['score'], '0')

        # Get user 2 to upvote
        self.assertTrue(vote(2, 1, 1))
        # Ensure post score has been adjusted
        self.assertEqual(get_comment(1)['score'], '0')
        # Ensure user score has been adjusted
        self.assertEqual(get_user(1)['score'], '1')
        # Ensure user 1 can not vote on there own comment
        self.assertFalse(vote(1, 1, 1))
        # Ensure the score didn't adjust (may be a code bug some day)
        # Ensure post score has been adjusted
        self.assertEqual(get_comment(1)['score'], '0')
        # Ensure user score has been adjusted
        self.assertEqual(get_user(1)['score'], '1')
        # Check to see if a user can vote twice on a comment
        self.assertFalse(vote(2, 1, 1))
        # Ensure the score didn't adjust (may be a code bug some day)
        # Ensure post score has been adjusted
        self.assertEqual(get_comment(1)['score'], '0')
        # Ensure user score has been adjusted
        self.assertEqual(get_user(1)['score'], '1')

    def test_delete(self):
        """
        Tests delete_post() does what it should.
        This will in turn test delete_comments() as this will be triggered when
        a post is deleted.
        """
        # Create three test users
        self.assertEqual(create_user('test1', 'test1@pjuu.com', 'Password'), 1)
        self.assertEqual(create_user('test2', 'test2@pjuu.com', 'Password'), 2)
        # Create a post
        self.assertEqual(create_post(1, 'Test post'), 1)
        # Create multiple comments
        self.assertEqual(create_comment(1, 1, 'Test comment 1'), 1)
        self.assertEqual(create_comment(2, 1, 'Test comment 2'), 2)
        self.assertEqual(create_comment(1, 1, 'Test comment 3'), 3)
        self.assertEqual(create_comment(2, 1, 'Test comment 4'), 4)
        # Test deleting one comment
        # This function does not actually test to see if the user has the
        # the rights to delete the post. This should be tested in the frontend
        # Check a comment can be deleted
        self.assertTrue(delete(2, 1, 4))
        # Check that getting the comment returns None
        self.assertIsNone(get_comment(4))
        # Ensure the comment is no longer in the posts comment list and no
        # longer in the users comment list
        self.assertNotIn('4', r.lrange(K.POST_COMMENTS % 4, 0, -1))
        self.assertNotIn('4', r.lrange(K.USER_COMMENTS % 4, 0, -1))
        # Just ensure that the previous comment is in user 2's comment list
        # and inside the post list
        self.assertNotIn('2', r.lrange(K.POST_COMMENTS % 4, 0, -1))
        self.assertNotIn('2', r.lrange(K.USER_COMMENTS % 4, 0, -1))
        # Delete the post. This should delete all the comments, we will check
        self.assertTrue(delete(2, 1))
        # Check that the post does not exist
        self.assertIsNone(get_post(1))
        # Check that non of the comments exist
        self.assertIsNone(get_comment(1))
        self.assertIsNone(get_comment(2))
        self.assertIsNone(get_comment(3))
        # Ensure that the posts comment list has been deleted
        self.assertFalse(r.exists(K.POST_COMMENTS % 1))
        # Ensure that non of the comments appear in the users comments lists
        self.assertNotIn('1', r.lrange(K.USER_COMMENTS % 1, 0, -1))
        self.assertNotIn('2', r.lrange(K.USER_COMMENTS % 2, 0, -1))
        self.assertNotIn('3', r.lrange(K.USER_COMMENTS % 1, 0, -1))

    def test_subscriptions(self):
        """
        Test the backend subscription system.

        This includes subscribe(), unsubscribe() and is_subscribed().

        This will also test the correct subscriptions after a post, comment or
        tagging.
        """
        # Create a couple of test accounts
        self.assertEqual(create_user('test1', 'test1@pjuu.com', 'Password'), 1)
        self.assertEqual(create_user('test2', 'test2@pjuu.com', 'Password'), 2)
        self.assertEqual(create_user('test3', 'test3@pjuu.com', 'Password'), 3)

        # Post as user 1 and ensure user 1 exists in Redis
        self.assertEqual(create_post(1, 'Test post 1'), 1)
        self.assertIsNotNone(r.zrank(K.POST_SUBSCRIBERS % 1, 1))

        # Even though it is exactly the same as the above ensure that
        # is_subscribed() returns True
        self.assertTrue(is_subscribed(1, 1))
        # Lets ensure this actually fails! And see if user two is a subscriber
        self.assertFalse(is_subscribed(2, 1))

        # Ensure that the REASON (zset score) is set to the correct value
        # This should be 1
        self.assertEqual(r.zscore(K.POST_SUBSCRIBERS % 1, 1), 1)

        # Post a comment as user 1 and ensure the reason does NOT changes
        self.assertEqual(create_comment(1, 1, 'Test comment 1'), 1)

        # Ensure our reason did not change
        # If we were not subscribed we would be given reason 2 (COMMENTOR)
        self.assertNotEqual(r.zscore(K.POST_SUBSCRIBERS % 1, 1), 2)

        # Test unsubscribe
        self.assertTrue(unsubscribe(1, 1))
        # Ensure that is_subscribed shows correct
        self.assertFalse(is_subscribed(1, 1))
        # Test that if we unsubscribe again we get a False result
        self.assertFalse(unsubscribe(1, 1))
        # Check that unsubscribing some that was never subscribed returns false
        self.assertFalse(unsubscribe(2, 1))

        # Let's test that commenting subscribes us to the post with the correct
        # reason
        self.assertEqual(create_comment(1, 1, 'Test comment 2'), 2)

        # Ensure we are subscribed
        self.assertTrue(is_subscribed(1, 1))

        # Check that our reason HAS changed
        self.assertEqual(r.zscore(K.POST_SUBSCRIBERS % 1, 1), 2)

        # Create a comment as test2 and ensure this user becomes subscribed for
        # the same reason
        self.assertEqual(create_comment(2, 1, 'Test comment 3'), 3)
        self.assertTrue(is_subscribed(2, 1))
        self.assertEqual(r.zscore(K.POST_SUBSCRIBERS % 1, 2), 2)

        # Create a new post as test1 and tag test2 and test3 in it
        # ensure all 3 are subscribed and test2 and test3 have the correct
        # reason
        self.assertEqual(create_post(1, 'Test post 2: @test2 @test3'), 2)
        self.assertTrue(is_subscribed(2, 2))
        self.assertTrue(is_subscribed(3, 2))
        self.assertEqual(r.zscore(K.POST_SUBSCRIBERS % 2, 2), 3)
        self.assertEqual(r.zscore(K.POST_SUBSCRIBERS % 2, 3), 3)

        # Unsubscribe test2 and test3
        self.assertTrue(unsubscribe(2, 2))
        self.assertFalse(is_subscribed(2, 2))
        self.assertTrue(unsubscribe(3, 2))
        self.assertFalse(is_subscribed(3, 2))

        # Create a comment as test1 and ensure tagging in a comment subscribes
        # users which are tagged
        self.assertEqual(create_comment(1, 2, 'Test post 2: @test2 @test3'), 4)
        self.assertTrue(is_subscribed(2, 2))
        self.assertTrue(is_subscribed(3, 2))
        self.assertEqual(r.zscore(K.POST_SUBSCRIBERS % 2, 2), 3)
        self.assertEqual(r.zscore(K.POST_SUBSCRIBERS % 2, 3), 3)
        # Done for now

    def test_alerts(self):
        """
        Unlike the test_alerts() definition in the users package this just
        tests that TaggingAlert and CommentingAlert are generated in the right
        situation
        """
        # Create 3 test users
        user1 = create_user('test1', 'test1@pjuu.com', 'Password')
        user2 = create_user('test2', 'test2@pjuu.com', 'Password')
        user3 = create_user('test3', 'test3@pjuu.com', 'Password')
        # No need to activate the accounts

        # User1 tag user2 in a post
        post1 = create_post(user1, 'Hello @test2')

        # Get alerts for test2 and check that it is correct
        alerts = get_alerts(user2).items
        alert = alerts[0]
        self.assertTrue(isinstance(alert, TaggingAlert))
        self.assertEqual(alert.get_username(), 'test1')
        self.assertEqual(alert.get_email(), 'test1@pjuu.com')
        self.assertIn('tagged you in a', alert.prettify())

        # Have user2 tag user3 in a comment
        create_comment(user2, post1, 'And you @test3')
        # Check the alerts again
        alerts = get_alerts(user3).items
        alert = alerts[0]
        self.assertTrue(isinstance(alert, TaggingAlert))
        self.assertEqual(alert.get_username(), 'test2')
        self.assertEqual(alert.get_email(), 'test2@pjuu.com')
        self.assertIn('tagged you in a', alert.prettify())

        # User 1 should now have a commenting alert from user2
        alerts = get_alerts(user1).items
        alert = alerts[0]
        self.assertTrue(isinstance(alert, CommentingAlert))
        self.assertEqual(alert.get_username(), 'test2')
        self.assertEqual(alert.get_email(), 'test2@pjuu.com')
        # Please remember that prettify requires a uid to format it too in the
        # case of a commenting alert
        self.assertIn('commented on a', alert.prettify(user1))
        self.assertIn('you posted', alert.prettify(user1))

        # Done for now
