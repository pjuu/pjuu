# -*- coding: utf8 -*-

"""Tests for ``auth.backend``.

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2020 Joe Doherty

"""

import json

from flask import current_app as app, session

from pjuu import mongo as m, redis as r
from pjuu.auth.backend import (
    create_account, delete_account, dump_account, authenticate, mute,
    bite, change_password, change_email, activate, ban, signin, signout,
    user_exists
)
from pjuu.auth.utils import get_uid, get_uid_email, get_uid_username
from pjuu.auth.stats import get_stats
from pjuu.lib import keys as K
from pjuu.posts.backend import create_post
from pjuu.users.backend import follow_user, get_user

from tests import BackendTestCase


class AuthBackendTests(BackendTestCase):
    """This case will test ALL ``auth.backend`` functions.

    """

    def test_create_user(self):
        """Check basic user creation stuffs.

        This also in turn tests check_username(), check_username_pattern(),
        check_email(), check_email_pattern(), get_username() and get_email().

        """
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        self.assertIsNotNone(user1)

        # Duplicate username
        self.assertIsNone(
            create_account('user1', 'userX@pjuu.com', 'Password'))

        # Duplicate email
        self.assertIsNone(
            create_account('userX', 'user1@pjuu.com', 'Password'))

        # Invalid username
        self.assertIsNone(
            create_account('u', 'userX@pjuu.com', 'Password'))

        # Invalid email
        self.assertIsNone(
            create_account('userX', 'userX', 'Password'))

        # Reserved username
        self.assertIsNone(
            create_account('help', 'userX@pjuu.com', 'Password'))

        # You can't get a UID for a non-activated user
        self.assertEqual(get_uid('user1'), None)

        activate(user1)
        self.assertEqual(get_uid('user1'), user1)
        self.assertEqual(get_uid('user1@pjuu.com'), user1)

        # Shouldn't work wiht invali users
        self.assertIsNone(get_user(K.NIL_VALUE))

        # Ensure if works with a valid user
        self.assertIsNotNone(get_user(user1))
        self.assertIsNotNone(type(get_user(user1)))
        self.assertEqual(type(get_user(user1)), dict)
        self.assertEqual(get_user(user1).get('username'), 'user1')
        self.assertEqual(get_user(user1).get('email'), 'user1@pjuu.com')

        # Check get_uid_* with invalid entries
        self.assertIsNone(get_uid_username('testymctest'))
        self.assertIsNone(get_uid_email('testymctest@pjuu.com'))

        # With valid
        self.assertEqual(get_uid_username('user1'), user1)
        self.assertEqual(get_uid_email('user1@pjuu.com'), user1)

        # Create a new user to check the defaults
        user2 = create_account('user2', 'user2@pjuu.com', 'Password')

        # Are values set as expected?
        user = get_user(user2)

        self.assertIsNotNone(user)
        self.assertEqual(user.get('_id'), user2)
        self.assertEqual(user.get('username'), 'user2')
        self.assertEqual(user.get('email'), 'user2@pjuu.com')
        self.assertEqual(user.get('last_login'), -1)
        self.assertFalse(user.get('active'))
        self.assertFalse(user.get('banned'))
        self.assertFalse(user.get('op'))
        self.assertFalse(user.get('muted'))
        self.assertEqual(user.get('about'), '')
        self.assertEqual(user.get('score'), 0)
        self.assertEqual(user.get('alerts_last_checked'), -1)
        self.assertIsNotNone(user.get('ttl'))

        # Generated values, we don't know what they SHOULD be
        self.assertIsNotNone(user.get('password'))
        self.assertIsNotNone(user.get('created'))

        # Check user_exists works
        self.assertTrue(user_exists(user1))
        # Check it fails when invalid value
        self.assertFalse(user_exists(K.NIL_VALUE))

    def test_userflags(self):
        """Ensure user flags are set as expected.

        """
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        self.assertIsNotNone(user1)

        # Not active by default
        self.assertFalse(get_user(user1).get('active'))
        # TTL should be set
        self.assertIsNotNone(get_user(user1).get('ttl'))
        # Activate
        self.assertTrue(activate(user1))
        self.assertTrue(get_user(user1).get('active'))
        self.assertIsNone(get_user(user1).get('ttl'))
        # Deactivate
        self.assertTrue(activate(user1, False))
        self.assertFalse(get_user(user1).get('active'))
        # Invalid
        self.assertFalse(activate(None))
        self.assertFalse(activate(K.NIL_VALUE))

        # Banning, not by default
        self.assertFalse(get_user(user1).get('banned'))
        # Ban
        self.assertTrue(ban(user1))
        self.assertTrue(get_user(user1).get('banned'))
        # Un-ban
        self.assertTrue(ban(user1, False))
        self.assertFalse(get_user(user1).get('banned'))
        # Invalid
        self.assertFalse(ban(None))
        self.assertFalse(ban(K.NIL_VALUE))

        # OP (Over powered or Operator?) Account should not be op
        self.assertFalse(get_user(user1).get('op'))
        # Bite
        self.assertTrue(bite(user1))
        self.assertTrue(get_user(user1).get('op'))
        # Un-bite
        self.assertTrue(bite(user1, False))
        self.assertFalse(get_user(user1).get('op'))
        # Invalid
        self.assertFalse(bite(None))
        self.assertFalse(bite(K.NIL_VALUE))

        # Muted, can't post, not by default
        self.assertFalse(get_user(user1).get('muted'))
        # Mute
        self.assertTrue(mute(user1))
        self.assertTrue(get_user(user1).get('muted'))
        # Un-mute
        self.assertTrue(mute(user1, False))
        self.assertFalse(get_user(user1).get('muted'))
        # Invalid
        self.assertFalse(mute(None))
        self.assertFalse(mute(K.NIL_VALUE))

    def test_authenticate(self):
        """Can a user be authenticated?

        """
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        self.assertIsNotNone(user1)

        # Check authenticate
        self.assertEqual(authenticate('user1', 'Password').get('_id'), user1)

        # Check auth with e-mail
        self.assertEqual(authenticate('user1@pjuu.com', 'Password').get('_id'),
                         user1)

        # Case in-sensitive test
        self.assertEqual(authenticate('USER1', 'Password').get('_id'), user1)
        self.assertEqual(authenticate('USER1@PJUU.COM', 'Password').get('_id'),
                         user1)

        # Ensure case in-sensitive password does NOT WORK
        self.assertIsNone(authenticate('user1', 'password'))
        self.assertIsNone(authenticate('user1', 'PASSWORD'))

        # Check incorrect password
        self.assertIsNone(authenticate('user1', 'Pass'))
        # Check non-existent user
        self.assertIsNone(authenticate('userX', 'Password'))
        # Check no glob username
        self.assertIsNone(authenticate('use*', 'Password'))
        # Check no glob password (just to be safe)
        self.assertIsNone(authenticate('user1', 'Passw*'))

    def test_login_logout(self):
        """Can a user log in (sign in) and log out (sign out)?

        Involves a request context but IS a backend function. Sessions needed.

        """
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        self.assertIsNotNone(user1)

        with app.test_request_context('/signin'):
            signin(user1)
            self.assertEqual(session.get('user_id', None), user1)

            signout()
            self.assertIsNone(session.get('user_id', None))

    def test_change_password(self):
        """Can a user change password?

        There is no sanity or restrictions on passwords in the backend.

        """
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')

        # Take current password (is hash don't string compare)
        current_password = get_user(user1).get('password')

        # Change password
        self.assertIsNotNone(change_password(user1, 'Password1'))
        new_password = get_user(user1).get('password')

        # Just check the hashed are different
        self.assertNotEqual(current_password, new_password)
        # Make sure the old password does not authenticate
        self.assertIsNone(authenticate('user1', 'Password'))
        # Check new password lets us log in
        self.assertEqual(authenticate('user1', 'Password1').get('_id'), user1)

    def test_change_email(self):
        """Can a user change their e-mail?

        """
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')

        # Test email lookup key
        self.assertEqual(get_uid_email('user1@pjuu.com'), None)

        activate(user1)
        self.assertEqual(get_uid_email('user1@pjuu.com'), user1)
        # Check correct email
        self.assertEqual(get_user(user1).get('email'), 'user1@pjuu.com')

        # Change e-mail
        self.assertIsNotNone(change_email(user1, 'userX@pjuu.com'))

        # Check new lookup key
        self.assertEqual(get_uid_email('userX@pjuu.com'), user1)
        # Check old lookup key has been nulled
        self.assertIsNone(get_uid_email('user1@pjuu.com'))

    def test_delete_account_basic(self):
        """Does the basic data go when a user delete their account?

        ..note: Just checks the auth part.

        """
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        self.assertIsNotNone(user1)

        delete_account(user1)

        self.assertIsNone(get_user(user1))
        self.assertIsNone(get_uid_username('user1'))
        self.assertIsNone(get_uid_email('user1@pjuu.com'))

        self.assertFalse(authenticate('user1', 'Password'))
        self.assertIsNone(get_uid_username('user1'))
        self.assertIsNone(get_uid_email('user1@pjuu.com'))

    def test_delete_account_posts_replies(self):
        """Do all posts and replies get removed on deletion of account?

        """
        user1 = create_account('user1', 'user2@pjuu.com', 'Password')
        user2 = create_account('user2', 'user2@pjuu.com', 'Password')

        post1 = create_post(user1, 'user1', 'Test post')
        post2 = create_post(user2, 'user2', 'Test post')

        # Create multiple comments on both posts
        comment1 = create_post(user1, 'user1', "Test comment", post1)
        create_post(user1, 'user1', "Test comment", post1)
        create_post(user1, 'user1', "Test comment", post1)
        create_post(user1, 'user1', "Test comment", post2)

        delete_account(user1)

        # All posts created by user1 and the replies on those post, gone?
        self.assertIsNone(m.db.posts.find_one({'_id': post1}))
        self.assertIsNone(m.db.posts.find_one({'reply_to': post1}))

        # Ensure the reply is gone
        self.assertIsNone(m.db.posts.find_one({'_id': comment1}))

        # Is feed empty?
        self.assertFalse(r.lrange(K.USER_FEED.format(user1), 0, -1))

    def test_delete_account_followers_following(self):
        """Does the users social graph go on deletion of account?

        """
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        user2 = create_account('user2', 'user2@pjuu.com', 'Password')

        # Friends :)
        self.assertTrue(follow_user(user1, user2))
        self.assertTrue(follow_user(user2, user1))

        # Ensure Redis's sorted sets are correct
        self.assertIn(user2, r.zrange(K.USER_FOLLOWERS.format(user1), 0, -1))
        self.assertIn(user2, r.zrange(K.USER_FOLLOWING.format(user1), 0, -1))
        self.assertIn(user1, r.zrange(K.USER_FOLLOWERS.format(user2), 0, -1))
        self.assertIn(user1, r.zrange(K.USER_FOLLOWING.format(user2), 0, -1))

        delete_account(user1)

        # Ensure sorted sets are emptied
        self.assertNotIn(user2, r.zrange(K.USER_FOLLOWERS.format(user1),
                                         0, -1))
        self.assertNotIn(user2, r.zrange(K.USER_FOLLOWING.format(user1),
                                         0, -1))
        self.assertNotIn(user1, r.zrange(K.USER_FOLLOWERS.format(user2),
                                         0, -1))
        self.assertNotIn(user1, r.zrange(K.USER_FOLLOWING.format(user2),
                                         0, -1))

    def test_dump_account(self):
        """Can a user get their data?

        """
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        activate(user1)

        data = dump_account(user1)
        self.assertIsNotNone(data)

        # Got data?
        self.assertEqual('user1', data['user']['username'])
        self.assertTrue(data['user']['active'])

        # Has sensitive data been removed?
        self.assertEqual('<UID>', data['user']['_id'])
        self.assertEqual('<PASSWORD HASH>', data['user']['password'])

        self.assertEqual([], data['posts'])

        # Can they dump posts?
        post1 = create_post(user1, 'user1', 'Post 1')
        post2 = create_post(user1, 'user1', 'Post 2')
        post3 = create_post(user1, 'user1', 'Post 3')

        data = dump_account(user1)
        self.assertIsNotNone(data)

        self.assertNotEqual([], data['posts'])
        self.assertEqual('Post 1', data['posts'][2]['body'])
        self.assertEqual('Post 2', data['posts'][1]['body'])
        self.assertEqual('Post 3', data['posts'][0]['body'])

        self.assertEqual('<UID>', data['posts'][0]['user_id'])

        # What about replies?
        create_post(user1, 'user1', 'Comment 1', post1)
        create_post(user1, 'user1', 'Comment 2', post1)
        create_post(user1, 'user1', 'Comment 3', post2)
        create_post(user1, 'user1', 'Comment 4', post3)

        data = dump_account(user1)
        self.assertNotEqual([], data['posts'])

        self.assertEqual('Comment 1', data['posts'][3]['body'])
        self.assertEqual('Comment 2', data['posts'][2]['body'])
        self.assertEqual('Comment 3', data['posts'][1]['body'])
        self.assertEqual('Comment 4', data['posts'][0]['body'])
        # Senstive data?
        self.assertEqual('<UID>', data['posts'][0]['user_id'])

        # Testing running dump account with a non-existent user
        self.assertIsNone(dump_account(K.NIL_VALUE))

        # Test that user id's a hidden in mentions
        user2 = create_account('user2', 'user2@pjuu.com', 'Password')
        activate(user2)

        user3 = create_account('user3', 'user3@pjuu.com', 'Password')
        activate(user3)

        post1 = create_post(user1, 'user1', 'Hello @user2')
        post_json = json.dumps(dump_account(user1))
        self.assertNotIn(user2, post_json)

        post2 = create_post(user1, 'user1', 'Hello @user2 and @user3')
        post_json = json.dumps(dump_account(user1))
        self.assertNotIn(user2, post_json)
        self.assertNotIn(user3, post_json)

    def test_stats(self):
        """Ensure the ``pjuu.auth.stats``s exposed stats are correct.

        """
        stats = dict(get_stats())

        self.assertEqual(stats.get('Total users'), 0)
        self.assertEqual(stats.get('Total active users'), 0)
        self.assertEqual(stats.get('Total banned users'), 0)
        self.assertEqual(stats.get('Total muted users'), 0)
        self.assertEqual(stats.get('Total OP users'), 0)
        self.assertEqual(stats.get('Newest users'), [])

        create_account('user1', 'user1@pjuu.com', 'Password')

        user2 = create_account('user2', 'user2@pjuu.com', 'Password')
        activate(user2)

        user3 = create_account('user3', 'user3@pjuu.com', 'Password')
        activate(user3)
        ban(user3)

        user4 = create_account('user4', 'user4@pjuu.com', 'Password')
        activate(user4)
        mute(user4)

        user5 = create_account('user5', 'user5@pjuu.com', 'Password')
        bite(user5)

        # Turn in to dict for easier checking.
        stats = dict(get_stats())

        # URL string to ensure links are being added in to newest users
        self.assertEqual(stats.get('Total users'), 5)
        self.assertEqual(stats.get('Total active users'), 3)
        self.assertEqual(stats.get('Total banned users'), 1)
        self.assertEqual(stats.get('Total muted users'), 1)
        self.assertEqual(stats.get('Total OP users'), 1)

        user_list = ['user5', 'user4', 'user3', 'user2', 'user1']
        newest_users = stats.get('Newest users')

        for i in range(len(newest_users)):
            self.assertIn(user_list[i], newest_users[i])
