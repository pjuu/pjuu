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
		assert create_user('test', 'test@pjuu.com', 'Password') == 1
		# Duplicate username
		assert create_user('test', 'testx@pjuu.com', 'Password') is None
		# Duplicate email
		assert create_user('testx', 'test@pjuu.com', 'Password') is None
		# Invalid username
		assert create_user('t', 'testx@pjuu.com', 'Password') is None
		# Invalid email
		assert create_user('testx', 'test', 'Password') is None
		# Reserved username
		assert create_user('help', 'testx@pjuu.com', 'Password') is None
		# Check lookup keys exist
		assert get_uid('test') == 1
		assert get_uid('test@pjuu.com') == 1
		# Make sure getting the user returns a dict
		assert get_user(1) is not None
		# Make sure no dict is returned for no user
		assert get_user(2) is None
		# Check other user functions
		assert get_email(1) == 'test@pjuu.com'
		assert get_email(2) is None

	def test_userflags(self):
		"""
		Checks the user flags. Such as active, banned, op
		"""
		# Create a test account
		assert create_user('test', 'test@pjuu.com', 'Password') == 1
		# Account should be not active
		assert is_active(1) is False
		# Activate
		assert activate(1) is True
		assert is_active(1) is True
		# Deactivate
		assert activate(1, False) is True
		assert is_active(1) is False
		# Test invalid is active
		assert is_active(2) is False
		assert is_active("test") is False

		# Account should not be banned
		assert is_banned(1) is False
		# Ban
		assert ban(1) is True
		assert is_banned(1) is True
		# Unban
		assert ban(1, False) is True
		assert is_banned(1) is False

		# Account should not be op
		assert is_op(1) is False
		# Bite
		assert bite(1) is True
		assert is_op(1) is True
		# Unbite (makes no sense)
		assert bite(1, False) is True
		assert is_op(1) is False

	def test_authenticate(self):
		"""
		Check a user can authenticate
		"""
		assert create_user('test', 'test@pjuu.com', 'Password') == 1
		# Check authenticate
		assert authenticate('test', 'Password') == 1
		# Check incorrect password
		assert authenticate('test', 'Pass') is None
		# Check non existant user
		assert authenticate('testx', 'Password') is None
		# Check no glob username
		assert authenticate('tes*', 'Password') is None
		# There is no way a glob password would work its a hash
		# lets be thourough though
		assert authenticate('test', 'Passw*') is None

	def test_change_password(self):
		"""
		This will test change_password(). Obviously
		"""
		# Create user
		assert create_user('test', 'test@pjuu.com', 'Password') == 1
		# Take current password (is hash don't string compare)
		current_password = r.hget(K.USER % 1, 'password')
		# Change password
		assert change_password(1, 'Password1') is not None
		new_password = r.hget(K.USER % 1, 'password')
		# Just check the hashed are different
		assert current_password != new_password
		# Make sure the old password does not authenticate
		assert authenticate('test', 'Password') is None
		# Check new password lets us log in
		assert authenticate('test', 'Password1') == 1

	def test_change_email(self):
		"""
		Test change_email().
		"""
		# Create user
		assert create_user('test', 'test@pjuu.com', 'Password') == 1
		# Test email lookup key
		assert get_uid_email('test@pjuu.com') == 1
		# Check correct email
		assert get_email(1) == 'test@pjuu.com'
		# Change e-mail
		assert change_email(1, 'testn@pjuu.com') is not None
		# Check new lookup key
		assert get_uid_email('testn@pjuu.com') == 1
		# Check old lookup key has been nulled
		assert get_uid_email('test@pjuu.com') is None
		# Check the old key is set to -1 and the expiration has been set
		assert int(r.get('uid:email:test@pjuu.com')) == -1
		assert int(r.ttl('uid:email:test@pjuu.com')) != -1
