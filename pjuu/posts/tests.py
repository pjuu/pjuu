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
		# Create post
		self.assertEqual(create_post(1, 'Test post'), 1)
		# Create comment
		self.assertEqual(create_comment(1, 1, 'Test comment'), 1)
		# Check the comment was created
		self.assertEqual(int(get_comment(1).get('cid', None)), 1)
		# Ensure the comment is the posts 'comment' list
		# Remember redis returns everything as a string
		# This will fail if decode response is not enabled
		self.assertIn(u'1', r.lrange(K.POST_COMMENTS % 1, 0 , -1))
		# Ensure the comment is also in the users 'comments' list
		self.assertIn(u'1', r.lrange(K.USER_COMMENTS % 1, 0, -1))
