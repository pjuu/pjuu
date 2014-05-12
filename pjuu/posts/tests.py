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
from pjuu import keys as K, redis as r
from pjuu.auth.backend import create_user
from .backend import *


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
		pass

	def test_delete(self):
		pass


class FrontendTests(unittest.TestCase):
	"""
	This test case will test all the posts subpackages; views, decorators
	and forms
	"""
	pass
