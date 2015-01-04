# -*- coding: utf8 -*-

"""
Description:
    Auth package unit tests

Licence:
    Copyright 2014-2015 Joe Doherty <joe@pjuu.com>

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

# Stdlib import
import json
# 3rd party imports
from flask import current_app as app, request, session, url_for, g
# Pjuu imports
from pjuu import redis as r
from pjuu.auth import current_user
from pjuu.auth.backend import *
from pjuu.lib import keys as K
from pjuu.posts.backend import create_post, create_comment
from pjuu.users.backend import follow_user
# Test imports
from tests import BackendTestCase


###############################################################################
# BACKEND #####################################################################
###############################################################################


class AuthBackendTests(BackendTestCase):
    """
    This case will test ALL auth backend functions.

    It will use the standard pjuu.redis connection to do this so ensure you
    are not using a production database. This will change in the near future
    when application factories are implemented.
    """

    def test_create_user(self):
        """
        We are going to insert multiple users in to the database and ensure
        they are all there. We will also try and signup with invalid
        credentials and with details we have already inserted.

        This also in turn tests check_username(), check_username_pattern(),
        check_email(), check_email_pattern(), get_username() and get_email()
        """
        # Account creation
        # Get the new user uid
        user1 = create_user('user1', 'user1@pjuu.com', 'Password')
        self.assertIsNotNone(user1)
        # Duplicate username
        self.assertIsNone(create_user('user1', 'userX@pjuu.com', 'Password'))
        # Duplicate email
        self.assertIsNone(create_user('userX', 'user1@pjuu.com', 'Password'))
        # Invalid username
        self.assertIsNone(create_user('u', 'userX@pjuu.com', 'Password'))
        # Invalid email
        self.assertIsNone(create_user('userX', 'userX', 'Password'))
        # Reserved username
        self.assertIsNone(create_user('help', 'userX@pjuu.com', 'Password'))
        # Check lookup keys exist
        self.assertEqual(get_uid('user1'), user1)
        self.assertEqual(get_uid('user1@pjuu.com'), user1)
        # Make sure get_user with no valid user returns None
        self.assertIsNone(get_user(K.NIL_VALUE))
        # Make sure getting the user returns a dict
        self.assertIsNotNone(get_user(user1))
        # Check other user functions
        # get_username()
        self.assertEqual(get_username(user1), 'user1')
        self.assertIsNone(get_username(K.NIL_VALUE))
        # get_email()
        self.assertEqual(get_email(user1), 'user1@pjuu.com')
        self.assertIsNone(get_email(K.NIL_VALUE))

        # Test other helpers function
        # Check get_uid_* with invalid entries
        self.assertIsNone(get_uid_username('testymctest'))
        self.assertIsNone(get_uid_email('testymctest@pjuu.com'))

        # Ensure that the TTL is set for all 3 keys which are created.
        # Username and e-mail look up keys and also the user account itself
        self.assertNotEqual(r.ttl(K.UID_USERNAME.format('user1')), -1)
        self.assertNotEqual(r.ttl(K.UID_EMAIL.format('user1@pjuu.com')), -1)
        self.assertNotEqual(r.ttl(K.USER.format(user1)), -1)

        # Test getting the user object and ensure all aspects of it are there.
        user1_hash = get_user(user1)
        # Check all the default values which we know up front
        # REMEMBER, everything comes out of Redis as a string
        self.assertIsNotNone(user1_hash)
        self.assertEqual(user1_hash.get('uid'), user1)
        self.assertEqual(user1_hash.get('username'), 'user1')
        self.assertEqual(user1_hash.get('email'), 'user1@pjuu.com')
        self.assertEqual(user1_hash.get('last_login'), '-1')
        self.assertEqual(user1_hash.get('active'), '0')
        self.assertEqual(user1_hash.get('banned'), '0')
        self.assertEqual(user1_hash.get('op'), '0')
        self.assertEqual(user1_hash.get('muted'), '0')
        self.assertEqual(user1_hash.get('about'), '')
        self.assertEqual(user1_hash.get('score'), '0')
        self.assertEqual(user1_hash.get('alerts_last_checked'), '0')
        # Check the values which are generated are not none
        self.assertIsNotNone(user1_hash.get('password'))
        self.assertIsNotNone(user1_hash.get('created'))

    def test_userflags(self):
        """
        Checks the user flags. Such as active, banned, op
        """
        # Create a test account
        user1 = create_user('user1', 'user1@pjuu.com', 'Password')
        self.assertIsNotNone(user1)
        # Account should be not active
        self.assertFalse(is_active(user1))
        # Activate
        self.assertTrue(activate(user1))
        self.assertTrue(is_active(user1))

        # Ensure that the TTL is removed from all 3 keys related to creating
        # a new user
        self.assertEqual(r.ttl(K.UID_USERNAME.format('user1')), -1)
        self.assertEqual(r.ttl(K.UID_EMAIL.format('user1@pjuu.com')), -1)
        self.assertEqual(r.ttl(K.USER.format(user1)), -1)

        # Deactivate
        self.assertTrue(activate(user1, False))
        self.assertFalse(is_active(user1), False)
        # Test invalid is active
        self.assertFalse(is_active(K.NIL_VALUE))

        # Broken is_active
        self.assertFalse(is_active(None))
        # Broken activate
        # Invalid type
        self.assertFalse(activate(None))
        # Non-existant user
        self.assertFalse(activate(K.NIL_VALUE))

        # Account should not be banned
        self.assertFalse(is_banned(user1))
        # Ban
        self.assertTrue(ban(user1))
        self.assertTrue(is_banned(user1))
        # Unban
        self.assertTrue(ban(user1, False))
        self.assertFalse(is_banned(user1))

        # Broken is_banned
        self.assertFalse(is_banned(None))
        # Broken ban
        self.assertFalse(ban(None))
        self.assertFalse(ban(K.NIL_VALUE))

        # Account should not be op
        self.assertFalse(is_op(user1))
        # Bite
        self.assertTrue(bite(user1))
        self.assertTrue(is_op(user1))
        # Unbite (makes no sense)
        self.assertTrue(bite(user1, False))
        self.assertFalse(is_op(user1))

        # Broken is_op
        self.assertFalse(is_op(None))
        # Broken bite
        self.assertFalse(bite(None))
        self.assertFalse(bite(K.NIL_VALUE))

        # Account should not be muted
        self.assertFalse(is_mute(user1))
        # Mute
        self.assertTrue(mute(user1))
        self.assertTrue(is_mute(user1))
        # Un-mute
        self.assertTrue(mute(user1, False))
        self.assertFalse(is_mute(user1))

        # Broken is_mute
        self.assertFalse(is_mute(None))
        # Broken mute
        self.assertFalse(mute(None))
        self.assertFalse(mute(K.NIL_VALUE))

    def test_authenticate(self):
        """
        Check a user can authenticate
        """
        # Create test user
        user1 = create_user('user1', 'user1@pjuu.com', 'Password')
        self.assertIsNotNone(user1)
        # Check authenticate
        self.assertEqual(authenticate('user1', 'Password'), user1)
        # Check incorrect password
        self.assertIsNone(authenticate('user1', 'Pass'))
        # Check non existant user
        self.assertIsNone(authenticate('userX', 'Password'))
        # Check no glob username
        self.assertIsNone(authenticate('use*', 'Password'))
        # There is no way a glob password would work its a hash
        # lets be thourough though
        self.assertIsNone(authenticate('user1', 'Passw*'))

    def test_login_logout(self):
        """
        Ensure that a uid is added to the session during login
        Ensure that the uid is missing from the session during logout

        Note that this is only backend relevant. login() does not check if a
        user is banned, active or anything else
        """
        user1 = create_user('user1', 'user1@pjuu.com', 'Password')
        self.assertIsNotNone(user1)
        # We need a request context to use the session
        with app.test_request_context('/signin'):
            # Log the new user in
            login(user1)
            # Check the uid is now in the session
            self.assertEqual(session.get('uid', None), user1)
            # Log the user out
            logout()
            # Ensure a KeyError is thrown (This will not happen in Pjuu)
            self.assertIsNone(session.get('uid', None))

    def test_change_password(self):
        """
        This will test change_password(). Obviously
        """
        # Create user
        user1 = create_user('user1', 'user1@pjuu.com', 'Password')
        # Take current password (is hash don't string compare)
        current_password = r.hget(K.USER.format(user1), 'password')
        # Change password
        self.assertIsNotNone(change_password(user1, 'Password1'))
        new_password = r.hget(K.USER.format(user1), 'password')
        # Just check the hashed are different
        self.assertNotEqual(current_password, new_password)
        # Make sure the old password does not authenticate
        self.assertIsNone(authenticate('user1', 'Password'))
        # Check new password lets us log in
        self.assertEqual(authenticate('user1', 'Password1'), user1)

    def test_change_email(self):
        """
        Test change_email().
        """
        # Create user
        user1 = create_user('user1', 'user1@pjuu.com', 'Password')
        # Test email lookup key
        self.assertEqual(get_uid_email('user1@pjuu.com'), user1)
        # Check correct email
        self.assertEqual(get_email(user1), 'user1@pjuu.com')
        # Change e-mail
        self.assertIsNotNone(change_email(user1, 'userX@pjuu.com'))
        # Check new lookup key
        self.assertEqual(get_uid_email('userX@pjuu.com'), user1)
        # Check old lookup key has been nulled
        self.assertIsNone(get_uid_email('user1@pjuu.com'))
        # Check the old key is set to NIL_VALUE and the expiration has been set
        self.assertEqual(
            r.get(K.UID_EMAIL.format('user1@pjuu.com')), K.NIL_VALUE)
        self.assertNotEqual(
            int(r.ttl(K.UID_EMAIL.format('user1@pjuu.com'))), -1)

    def test_delete_account_basic(self):
        """
        Test delete_account()

        Posts and comments: Ensures that all data related to posting and
        commenting is removed
        """
        # Create test user
        user1 = create_user('user1', 'user1@pjuu.com', 'Password')
        self.assertIsNotNone(user1)
        # Lets just delete a fresh account
        delete_account(user1)
        # Lets check that has got rid of everything
        self.assertIsNone(get_user(user1))
        # Ensure the user can not be looked up
        self.assertIsNone(get_uid_username('user1'))
        self.assertIsNone(get_uid_email('user1@pjuu.com'))
        # Ensure the underlying Redis is correct
        # Ensure the user account has gone
        self.assertIsNone(r.get(K.USER.format(user1)))
        # Ensure the username maps to -1
        self.assertEqual(r.get(K.UID_USERNAME.format('user1')), K.NIL_VALUE)
        # Ensure the usernames TTL has been set
        self.assertNotEqual(int(r.ttl(K.UID_USERNAME.format('user1'))), -1)
        # Ensure the email maps to -1
        self.assertEqual(
            r.get(K.UID_EMAIL.format('user1@pjuu.com')), K.NIL_VALUE)
        # Ensure the email TTL has been set
        self.assertNotEqual(
            int(r.ttl(K.UID_EMAIL.format('user1@pjuu.com'))), -1)
        # Try and authenticate a user now that it has been deleted.
        # I have seen this cause issues during development
        self.assertFalse(authenticate('user1', 'Password'))
        self.assertIsNone(get_uid_username('user1'))
        self.assertIsNone(get_uid_email('user1@pjuu.com'))

    def test_delete_account_posts_comments(self):
        """
        Test delete_account()

        Posts and comments: Ensure all posts and comments are gone.

        Note: This is not a full test of the posts system. See posts/test.py
        """
        # Create test user
        user1 = create_user('user1', 'user2@pjuu.com', 'Password')
        # Second user to test deletion from user:1:comments
        user2 = create_user('user2', 'user2@pjuu.com', 'Password')
        # Create a post as both users
        post1 = create_post(user1, "Test post")
        post2 = create_post(user2, "Test post")
        # Create multiple comments on both posts
        # Post 1
        comment1 = create_comment(user1, post1, "Test comment")
        comment2 = create_comment(user1, post1, "Test comment")
        # Post 2
        comment3 = create_comment(user1, post2, "Test comment")
        comment4 = create_comment(user1, post2, "Test comment")

        # Delete the account
        delete_account(user1)

        # Ensure the Post, its comment list and votes has gone
        self.assertFalse(r.hgetall(K.POST.format(post1)))
        self.assertFalse(r.lrange(K.POST_COMMENTS.format(post1), 0, -1))
        # Ensure the Comment is gone
        self.assertFalse(r.hgetall(K.COMMENT.format(comment1)))
        # Assert feed is empty
        self.assertFalse(r.lrange(K.USER_FEED.format(user1), 0, -1))
        # Assert posts is empty
        self.assertFalse(r.lrange(K.USER_POSTS.format(user1), 0, -1))
        # Assert comments is empty
        self.assertFalse(r.lrange(K.USER_COMMENTS.format(user1), 0, -1))

    def test_delete_account_followers_following(self):
        """
        Test delete_account()

        Followers & Following: Ensures that all data related to followers is
        removed during account deletion

        Note: This is not a full test of the users system. See users/test.py
        """
        # Create test users
        user1 = create_user('user1', 'user1@pjuu.com', 'Password')
        user2 = create_user('user2', 'user2@pjuu.com', 'Password')
        # Make users follow each other
        self.assertTrue(follow_user(user1, user2))
        self.assertTrue(follow_user(user2, user1))
        # Ensure the uid's are in the relevant sorted sets
        self.assertIn(user2, r.zrange(K.USER_FOLLOWERS.format(user1), 0, -1))
        self.assertIn(user2, r.zrange(K.USER_FOLLOWING.format(user1), 0, -1))
        self.assertIn(user1, r.zrange(K.USER_FOLLOWERS.format(user2), 0, -1))
        self.assertIn(user1, r.zrange(K.USER_FOLLOWING.format(user2), 0, -1))

        # Delete test account 1
        delete_account(user1)

        # Ensure the lists are empty
        self.assertNotIn(user2, r.zrange(K.USER_FOLLOWERS.format(user1),
                                         0, -1))
        self.assertNotIn(user2, r.zrange(K.USER_FOLLOWING.format(user1),
                                         0, -1))
        self.assertNotIn(user1, r.zrange(K.USER_FOLLOWERS.format(user2),
                                         0, -1))
        self.assertNotIn(user1, r.zrange(K.USER_FOLLOWING.format(user2),
                                         0, -1))

    def test_dump_account(self):
        """
        Test dump_account. We will create some posts and comments and check all
        this data appears in the dumps

        Remember that ALL data coming out of Redis is a string. We are not
        going to convert each type. EVERYTHING IS A STRING
        """
        user1 = create_user('user1', 'user1@pjuu.com', 'Password')

        # Dump the account so that we can test :D
        data = dump_account(user1)

        # Check we got some data
        self.assertIsNotNone(data)
        # Ensure that we can see the data in the 'user' key
        self.assertEqual('user1', data['user']['username'])
        self.assertEqual('0', data['user']['active'])
        # Check that uid and password have been scrubbed
        self.assertEqual('<UID>', data['user']['uid'])
        self.assertEqual('<PASSWORD HASH>', data['user']['password'])
        # Ensure posts and comments are None
        self.assertEqual([], data['posts'])
        self.assertEqual([], data['comments'])

        # Create some posts as the user and check they are in the dumps
        post1 = create_post(user1, 'Post 1')
        post2 = create_post(user1, 'Post 2')
        post3 = create_post(user1, 'Post 3')

        data = dump_account(user1)
        self.assertIsNotNone(data)
        # Ensure that the posts are there
        self.assertNotEqual([], data['posts'])
        self.assertEqual('Post 1', data['posts'][2]['body'])
        self.assertEqual('Post 2', data['posts'][1]['body'])
        self.assertEqual('Post 3', data['posts'][0]['body'])
        # Ensure there is no a uid in the post
        self.assertEqual('<UID>', data['posts'][0]['uid'])

        # Create some comments on the above posts and re-dump
        comment1 = create_comment(user1, post1, 'Comment 1')
        comment2 = create_comment(user1, post1, 'Comment 2')
        comment3 = create_comment(user1, post2, 'Comment 3')
        comment4 = create_comment(user1, post3, 'Comment 4')

        # Re-dump the database
        data = dump_account(user1)
        self.assertNotEqual([], data['comments'])
        # Check that all 4 comments have been dumped

        self.assertEqual('Comment 1', data['comments'][3]['body'])
        self.assertEqual('Comment 2', data['comments'][2]['body'])
        self.assertEqual('Comment 3', data['comments'][1]['body'])
        self.assertEqual('Comment 4', data['comments'][0]['body'])

        # Testing running dump account with a non-existant user
        self.assertIsNone(dump_account(K.NIL_VALUE))

        # This is a very basic test. May need expanding in the future
