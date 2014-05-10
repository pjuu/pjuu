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
from pjuu.auth.backend import create_user, delete_account
from pjuu.posts.backend import create_post, create_comment
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
		self.assertIn(u'1', r.lrange(K.USER_FEED % 1, 0, -1))
		# Create a second user, make 1 follow them, make them post and ensure
		# that the news users post appears in user 1s feed
		self.assertEqual(create_user('test2', 'test2@pjuu.com', 'Password'), 2)
		self.assertTrue(follow_user(1, 2))
		self.assertEqual(create_post(2, 'Test post'), 2)
		# Check user 1's feed for the next item
		self.assertEqual(len(get_feed(1).items), 2)
		self.assertEqual(get_feed(1).total, 2)
		# Ensure the item is in Redis
		self.assertIn(u'2', r.lrange(K.USER_FEED % 1, 0, -1))
		# Delete user 2 and ensure user 1's feed cleans itself
		delete_account(2)
		self.assertEqual(len(get_feed(1).items), 1)
		self.assertEqual(get_feed(1).total, 1)
		# Ensure the item is in Redis
		self.assertNotIn(u'2', r.lrange(K.USER_FEED % 1, 0, -1))


class FrontendTests(unittest.TestCase):
	"""
	This test case will test all the users subpackages; views, decorators
	and forms
	"""
	pass