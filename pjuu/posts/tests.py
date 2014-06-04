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
import unittest
# Pjuu imports
from pjuu import redis as r
from pjuu.lib import keys as K
from pjuu.auth.backend import create_user, get_user
from .backend import *

###############################################################################
# BACKEND #####################################################################
###############################################################################

class BackendTests(unittest.TestCase):
    """
    This case will test ALL post backend functions.
    """

    def setUp(self):
        """
        Simply flush the database, we do not want any data already in redis
        changing the outcome of the tests
        """
        r.flushdb()

    def tearDown(self):
        """
        Simply flush the database. Keep it clean for other tests
        """
        r.flushdb()

    def test_create_post(self):
        """
        Tests creating a post
        """
        # Create a user to test creating post
        self.assertEqual(create_user('test', 'test@pjuu.com', 'Password'), 1)
        # Create post
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
        # Create post
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
        self.assertIn(u'1', r.lrange(K.POST_COMMENTS % 1, 0 , -1))
        # Ensure the comment is also in the users 'comments' list
        self.assertIn(u'1', r.lrange(K.USER_COMMENTS % 1, 0, -1))
        # Ensure the same applies for the second users post
        self.assertIn(u'2', r.lrange(K.POST_COMMENTS % 1, 0 , -1))
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
        # Attempt to get a non existant comment
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
        # Get user 2 to upvote
        self.assertTrue(vote(2, 1))
        # Ensure post score has been adjusted
        self.assertEqual(get_post(1)['score'], '1')
        # Ensure user score has been adjusted
        self.assertEqual(get_user(1)['score'], '1')
        # Get user 3 to downvote
        self.assertTrue(vote(3, 1, amount=-1))
        # Ensure post score has been adjusted
        self.assertEqual(get_post(1)['score'], '0')
        # Ensure user score has been adjusted
        self.assertEqual(get_user(1)['score'], '0')
        # Ensure user 1 can not vote on there own comment
        self.assertFalse(vote(1, 1))
        # Ensure the score didn't adjust (may be a code bug some day)
        # Ensure post score has been adjusted
        self.assertEqual(get_post(1)['score'], '0')
        # Ensure user score has been adjusted
        self.assertEqual(get_user(1)['score'], '0')
        # Check to see if a user can vote twice on a comment
        self.assertFalse(vote(2, 1))
        # Ensure the score didn't adjust (may be a code bug some day)
        # Ensure post score has been adjusted
        self.assertEqual(get_post(1)['score'], '0')
        # Ensure user score has been adjusted
        self.assertEqual(get_user(1)['score'], '0')        
        # Repeat the same tests on a comment
        # Create a comment by user 1
        self.assertEqual(create_comment(1, 1, 'Test post'), 1)
        # Get user 2 to upvote
        self.assertTrue(vote(2, 1, 1))
        # Ensure post score has been adjusted
        self.assertEqual(get_comment(1)['score'], '1')
        # Ensure user score has been adjusted
        self.assertEqual(get_user(1)['score'], '1')
        # Get user 3 to downvote
        self.assertTrue(vote(3, 1, 1, amount=-1))
        # Ensure post score has been adjusted
        self.assertEqual(get_comment(1)['score'], '0')
        # Ensure user score has been adjusted
        self.assertEqual(get_user(1)['score'], '0')
        # Ensure user 1 can not vote on there own comment
        self.assertFalse(vote(1, 1, 1))
        # Ensure the score didn't adjust (may be a code bug some day)
        # Ensure post score has been adjusted
        self.assertEqual(get_comment(1)['score'], '0')
        # Ensure user score has been adjusted
        self.assertEqual(get_user(1)['score'], '0')
        # Check to see if a user can vote twice on a comment
        self.assertFalse(vote(2, 1, 1))
        # Ensure the score didn't adjust (may be a code bug some day)
        # Ensure post score has been adjusted
        self.assertEqual(get_comment(1)['score'], '0')
        # Ensure user score has been adjusted
        self.assertEqual(get_user(1)['score'], '0')                

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
        # Just ensure that the previous comment is in user 2's comment list
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

###############################################################################
# FRONTEND ####################################################################
###############################################################################

class FrontendTests(unittest.TestCase):
    """
    This test case will test all the posts subpackages; views, decorators
    and forms
    """

    def setUp(self):
        """
        Flush the database and create a test client so that we can check all
        end points.
        """
        r.flushdb()
        # Get our test client
        self.client = app.test_client()

    def tearDown(self):
        """
        Simply flush the database. Keep it clean for other tests
        """
        r.flushdb()

    def test_post(self):
        pass

    def test_comment(self):
        pass

    def test_upvote(self):
        pass

    def test_downvote(self):
        pass

    def test_delete_post(self):
        pass
