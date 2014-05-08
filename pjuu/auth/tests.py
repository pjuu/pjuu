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
# 3rd party imports
from flask import _app_ctx_stack, request, session
from redis import StrictRedis
# Pjuu imports
from pjuu import app, keys as K, redis as r
from pjuu.users.backend import follow_user
from pjuu.posts.backend import create_post, create_comment
from . import current_user
from .backend import *


class BackendTests(unittest.TestCase):
	"""
	This case will test ALL auth backend functions.

	It will use the standard pjuu.redis connection to do this so ensure you
	are not using a production database. This will change in the near future
	when application factories are implemented.
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

	def test_create_user(self):
		"""
		We are going to insert multiple users in to the database and ensure
		they are all there. We will also try and signup with invalid
		credentials and with details we have already inserted.

		This also in turn tests check_username() and check_email()
		"""
		# Account creation
		self.assertEqual(create_user('test', 'test@pjuu.com', 'Password'), 1)
		# Duplicate username
		self.assertIsNone(create_user('test', 'testx@pjuu.com', 'Password'))
		# Duplicate email
		self.assertIsNone(create_user('testx', 'test@pjuu.com', 'Password'))
		# Invalid username
		self.assertIsNone(create_user('t', 'testx@pjuu.com', 'Password'))
		# Invalid email
		self.assertIsNone(create_user('testx', 'test', 'Password'))
		# Reserved username
		self.assertIsNone(create_user('help', 'testx@pjuu.com', 'Password'))
		# Check lookup keys exist
		self.assertEqual(get_uid('test'), 1)
		self.assertEqual(get_uid('test@pjuu.com'), 1)
		# Make sure getting the user returns a dict
		self.assertIsNotNone(get_user(1))
		# Make sure no dict is returned for no user
		self.assertIsNone(get_user(2))
		# Check other user functions
		self.assertEqual(get_email(1), 'test@pjuu.com')
		self.assertIsNone(get_email(2))

	def test_userflags(self):
		"""
		Checks the user flags. Such as active, banned, op
		"""
		# Create a test account
		self.assertEqual(create_user('test', 'test@pjuu.com', 'Password'), 1)
		# Account should be not active
		self.assertFalse(is_active(1))
		# Activate
		self.assertTrue(activate(1))
		self.assertTrue(is_active(1))
		# Deactivate
		self.assertTrue(activate(1, False))
		self.assertFalse(is_active(1), False)
		# Test invalid is active
		self.assertFalse(is_active(2))
		self.assertFalse(is_active("test"))

		# Account should not be banned
		self.assertFalse(is_banned(1))
		# Ban
		self.assertTrue(ban(1))
		self.assertTrue(is_banned(1))
		# Unban
		self.assertTrue(ban(1, False))
		self.assertFalse(is_banned(1))

		# Account should not be op
		self.assertFalse(is_op(1))
		# Bite
		self.assertTrue(bite(1))
		self.assertTrue(is_op(1))
		# Unbite (makes no sense)
		self.assertTrue(bite(1, False))
		self.assertFalse(is_op(1))

	def test_authenticate(self):
		"""
		Check a user can authenticate
		"""
		self.assertEqual(create_user('test', 'test@pjuu.com', 'Password'), 1)
		# Check authenticate
		self.assertEqual(authenticate('test', 'Password'), 1)
		# Check incorrect password
		self.assertIsNone(authenticate('test', 'Pass'))
		# Check non existant user
		self.assertIsNone(authenticate('testx', 'Password'))
		# Check no glob username
		self.assertIsNone(authenticate('tes*', 'Password'))
		# There is no way a glob password would work its a hash
		# lets be thourough though
		self.assertIsNone(authenticate('test', 'Passw*'))

	def test_login_logout(self):
		"""
		Ensure that a uid is added to the session during login
		Ensure that the uid is missing from the session during logout

		Note that this is only backend relevant. login() does not check if a
		user is banned, active or anything else
		"""
		self.assertEqual(create_user('test', 'test@pjuu.com', 'Password'), 1)
		# We need a request context to use the session
		with app.test_request_context('/signin'):
			# Log the new user in
			login(1)
			# Check the uid is now in the session
			self.assertEqual(session.get('uid', None), 1)
			# Log the user out
			logout()
			# Ensure a KeyError is thrown (This will not happen in Pjuu)
			self.assertIsNone(session.get('uid', None))

	def test_change_password(self):
		"""
		This will test change_password(). Obviously
		"""
		# Create user
		self.assertEqual(create_user('test', 'test@pjuu.com', 'Password'), 1)
		# Take current password (is hash don't string compare)
		current_password = r.hget(K.USER % 1, 'password')
		# Change password
		self.assertIsNotNone(change_password(1, 'Password1'))
		new_password = r.hget(K.USER % 1, 'password')
		# Just check the hashed are different
		self.assertNotEqual(current_password, new_password)
		# Make sure the old password does not authenticate
		self.assertIsNone(authenticate('test', 'Password'))
		# Check new password lets us log in
		self.assertEqual(authenticate('test', 'Password1'), 1)

	def test_change_email(self):
		"""
		Test change_email().
		"""
		# Create user
		self.assertEqual(create_user('test', 'test@pjuu.com', 'Password'), 1)
		# Test email lookup key
		self.assertEqual(get_uid_email('test@pjuu.com'), 1)
		# Check correct email
		self.assertEqual(get_email(1), 'test@pjuu.com')
		# Change e-mail
		self.assertIsNotNone(change_email(1, 'testn@pjuu.com'))
		# Check new lookup key
		self.assertEqual(get_uid_email('testn@pjuu.com'), 1)
		# Check old lookup key has been nulled
		self.assertIsNone(get_uid_email('test@pjuu.com'))
		# Check the old key is set to -1 and the expiration has been set
		self.assertEqual(int(r.get(K.UID_EMAIL % 'test@pjuu.com')), -1)
		self.assertNotEqual(int(r.ttl(K.UID_EMAIL % 'test@pjuu.com')), -1)

	def test_delete_account_basic(self):
		"""
		Test delete_account()

		Posts and comments: Ensures that all data related to posting and
		commenting is removed
		"""
		# Create test user
		self.assertEqual(create_user('test', 'test@pjuu.com', 'Password'), 1)
		# Lets just delete a fresh account
		delete_account(1)
		# Lets check that has got rid of everything
		self.assertIsNone(get_user(1))
		# Ensure the user can not be looked up
		self.assertIsNone(get_uid_username('test'))
		self.assertIsNone(get_uid_email('test@pjuu.com'))
		# Ensure the underlying Redis is correct
		# Ensure the user account has gone
		self.assertIsNone(r.get(K.USER % 1))
		# Ensure the username maps to -1
		self.assertEqual(int(r.get(K.UID_USERNAME % 'test')), -1)
		# Ensure the usernames TTL has been set
		self.assertNotEqual(int(r.ttl(K.UID_USERNAME % 'test')), -1)
		# Ensure the email maps to -1
		self.assertEqual(int(r.get(K.UID_EMAIL % 'test@pjuu.com')), -1)
		# Ensure the email TTL has been set
		self.assertNotEqual(int(r.ttl(K.UID_EMAIL % 'test@pjuu.com')), -1)

	def test_delete_account_posts_comments(self):
		"""
		Test delete_account()

		Posts and comments: Ensure all posts and comments are gone.

		Note: This is not a full test of the posts system. See posts/test.py
		"""
		# Create test user
		self.assertEqual(create_user('test', 'test@pjuu.com', 'Password'), 1)
		# Create a post
		self.assertEqual(create_post(1, "Test post"), 1)
		# Create a comment
		self.assertEqual(create_comment(1, 1, "Test comment"), 1)

		# Ensure all the keys have been set
		self.assertTrue(r.hgetall(K.POST % 1))
		self.assertTrue(r.lrange(K.POST_COMMENTS % 1, 0, -1))
		# Ensure the Comment and its votes are gone
		self.assertTrue(r.hgetall(K.COMMENT % 1))
		# Assert feed has 1 item on it
		self.assertIn(u'1', r.lrange(K.USER_FEED % 1, 0, -1))
		# Assert posts is empty
		self.assertIn(u'1', r.lrange(K.USER_POSTS % 1, 0, -1))
		# Asset comments is empty
		self.assertIn(u'1', r.lrange(K.USER_COMMENTS % 1, 0, -1))

		# Delete the account
		delete_account(1)

		# Ensure the Post, its comment list and votes has gone
		self.assertFalse(r.hgetall(K.POST % 1))
		self.assertFalse(r.lrange(K.POST_COMMENTS % 1, 0, -1))
		# Ensure the Comment is gone
		self.assertFalse(r.hgetall(K.COMMENT % 1))
		# Assert feed is empty
		self.assertFalse(r.lrange(K.USER_FEED % 1, 0, -1))
		# Assert posts is empty
		self.assertFalse(r.lrange(K.USER_POSTS % 1, 0, -1))
		# Asset comments is empty
		self.assertFalse(r.lrange(K.USER_COMMENTS % 1, 0, -1))

	def test_delete_account_followers_following(self):
		"""
		Test delete_account()

		Followers & Following: Ensures that all data related to followers is
		removed during account deletion

		Note: This is not a full test of the users system. See users/test.py
		"""
		# Create test user 1
		self.assertEqual(create_user('test1', 'test1@pjuu.com', 'Password'), 1)
		# Create test user 2
		self.assertEqual(create_user('test2', 'test2@pjuu.com', 'Password'), 2)
		# Make users follow each other
		self.assertTrue(follow_user(1, 2))
		self.assertTrue(follow_user(2, 1))
		# Ensure the uid's are in the relevant sorted sets
		self.assertIn(u'2', r.zrange(K.USER_FOLLOWERS % 1, 0, -1))
		self.assertIn(u'2', r.zrange(K.USER_FOLLOWING % 1, 0, -1))
		self.assertIn(u'1', r.zrange(K.USER_FOLLOWERS % 2, 0, -1))
		self.assertIn(u'1', r.zrange(K.USER_FOLLOWING % 2, 0, -1))

		# Delete test account 1
		delete_account(1)

		# Ensure the lists are empty
		self.assertNotIn(u'2', r.zrange(K.USER_FOLLOWERS % 1, 0, -1))
		self.assertNotIn(u'2', r.zrange(K.USER_FOLLOWING % 1, 0, -1))
		self.assertNotIn(u'1', r.zrange(K.USER_FOLLOWERS % 2, 0, -1))
		self.assertNotIn(u'1', r.zrange(K.USER_FOLLOWING % 2, 0, -1))


class FrontendTests(unittest.TestCase):
	"""
	This test case will test all the auth subpackages views, decorators
	and forms
	"""
	pass
