# -*- coding: utf8 -*-

"""
Description:
    Auth package unit tests

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
import unittest
# 3rd party imports
from flask import current_app as app, request, session, url_for, g
# Pjuu imports
from pjuu import redis as r
from pjuu.lib import keys as K
from pjuu.users.backend import follow_user
from pjuu.posts.backend import create_post, create_comment
from . import current_user
from .backend import *

###############################################################################
# BACKEND #####################################################################
###############################################################################

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
        # get_username()
        self.assertEqual(get_username(1), 'test')
        self.assertIsNone(get_username(2))        
        # get_email()
        self.assertEqual(get_email(1), 'test@pjuu.com')
        self.assertIsNone(get_email(2))

        # Ensure that the TTL is set for all 3 keys which are created.
        # Username and e-mail look up keys and also the user account itself
        self.assertNotEqual(r.ttl(K.UID_USERNAME % 'test'), -1)
        self.assertNotEqual(r.ttl(K.UID_EMAIL % 'test@pjuu.com'), -1)
        self.assertNotEqual(r.ttl(K.USER % 1), -1)

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

        # Ensure that the TTL is removed from all 3 keys related to creating
        # a new user
        self.assertEqual(r.ttl(K.UID_USERNAME % 'test'), -1)
        self.assertEqual(r.ttl(K.UID_EMAIL % 'test@pjuu.com'), -1)
        self.assertEqual(r.ttl(K.USER % 1), -1)

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
        # Try and authenticate a user now that it has been deleted.
        # I have seen this cause issues during development
        self.assertFalse(authenticate('test', 'Password'))
        self.assertIsNone(get_uid_username('test'))
        self.assertIsNone(get_uid_email('test@pjuu.com'))

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

###############################################################################
# FRONTEND ####################################################################
###############################################################################

class FrontendTests(unittest.TestCase):
    """
    This test case will test all the auth subpackages views, decorators
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
        # Clear g token
        # TODO Get a better solution for this
        g.token = None
        # Get request context
        self.ctx = app.test_request_context()
        self.ctx.push()

    def tearDown(self):
        """
        Simply flush the database. Keep it clean for other tests
        """
        self.ctx.pop()
        r.flushdb()

    def test_signin_signout(self):
        """
        These functions will test the signin and signout endpoints. We will use
        url_for so that we can change the URIs in the future.
        """
        # Test that we can GET the signin page
        resp = self.client.get(url_for('signin'))
        # We should get a 200 with an error message if we were not successful
        self.assertEqual(resp.status_code, 200)

        # There is no user in the system check that we can't authenticate
        resp = self.client.post(url_for('signin'), data={
                'username': 'test',
                'password': 'Password'
            })
        # We should get a 200 with an error message if we were not successful
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Invalid user name or password', resp.data)

        # Why we are here we will just check that logging in doesn't raise an
        # issue if not logged in
        resp = self.client.get(url_for('signout'))
        # We should be 302 redirected to /signin
        self.assertEqual(resp.status_code, 302)    
        # There is nothing we can really check as we do not flash() as message

        # Create a test user and try loggin in, should fail as the user isn't
        # activated
        self.assertEqual(create_user('test', 'test@pjuu.com', 'Password'), 1)
        resp = self.client.post(url_for('signin'), data={
                'username': 'test',
                'password': 'Password'
            })
        # We should get a 200 with an information message
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Please activate your account', resp.data)

        # Activate account
        self.assertTrue(activate(1))

        # Test that the correct warning is shown if the user is banned
        self.assertTrue(ban(1))
        resp = self.client.post(url_for('signin'), data={
                'username': 'test',
                'password': 'Password'
            })
        # We should get a 200 with an information message
        self.assertEqual(resp.status_code, 200)
        self.assertIn('You\'re a very naughty boy!', resp.data)
        # Lets unban the user now so we can carry on
        self.assertTrue(ban(1, False))

        # Now the user is active and not banned actuall log in
        resp = self.client.post(url_for('signin'), data={
                'username': 'test',
                'password': 'Password'
            }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('<h1>Feed</h1>', resp.data)

        # Attempt to try and get back to login when we are already logged in
        resp = self.client.get(url_for('signin'))
        self.assertEqual(resp.status_code, 302)

        # Now we are logged in lets just ensure logout doesn't do anything daft
        # We should be redirected back to /
        resp = self.client.get(url_for('signout'), follow_redirects=True)
        # We should have been 302 redirected to /signin
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Successfully signed out', resp.data)

        # We will now ban the user just to ensure they can't get in. They
        # should receive a 200 and a warning message
        self.assertTrue(ban(1))
        resp = self.client.post(url_for('signin'), data={
                'username': 'test',
                'password': 'Password'
            })
        self.assertEqual(resp.status_code, 200)
        self.assertIn('You\'re a very naughty boy!', resp.data)
        # Unban the user so we can use it again
        self.assertTrue(ban(1, False), True)

        # Lets try and cheat the system
        # Attempt invalid Password
        resp = self.client.post(url_for('signin'), data={
                'username': 'test',
                'password': 'Password1'
            })
        # We should get a 200 with an error message if we were not successful
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Invalid user name or password', resp.data)

        # Attempt user does not exist
        resp = self.client.post(url_for('signin'), data={
                'username': 'test1',
                'password': 'Password1'
            })
        # We should get a 200 with an error message if we were not successful
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Invalid user name or password', resp.data)

        # Log the user in and ensure they are logged out if there account
        # is banned during using the site and not just at login
        resp = self.client.post(url_for('signin'), data={
                'username': 'test',
                'password': 'Password'
            }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('<h1>Feed</h1>', resp.data)
        # Lets go to another view, we will check out profile and look for our
        # username
        resp = self.client.get(url_for('settings_profile'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('test@pjuu.com', resp.data)
        # Let's ban the user now
        self.assertTrue(ban(1))
        # Attempt to get to the feed
        resp = self.client.get(url_for('feed'), follow_redirects=True)
        # We should be redirected to signin with the standard message
        self.assertEqual(resp.status_code, 200)
        self.assertIn('You\'re a very naughty boy!', resp.data)

    def test_signup_activate(self):
        """
        Tests the signup and activate endpoint inside Pjuu.

        There are some limitations to this! We can not test e-mail sending as
        this will not be available on Travis.
        """
        # Test that we can GET the signup page
        resp = self.client.get(url_for('signup'))
        # We should get a 200 with an error message if we were not successful
        self.assertEqual(resp.status_code, 200)

        # Lets attempt to create a new account. This should return a 302 to
        # /signin with a little message displayed to activate your account
        resp = self.client.post(url_for('signup'), data={
                'username': 'test',
                'email': 'test@pjuu.com',
                'password': 'Password',
                'password2': 'Password'
            }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Yay! You\'ve signed up', resp.data)
        # We are in testing mode so we can get the auth token from the response
        # this is in the headers as X-Pjuu-Token
        token = resp.headers.get('X-Pjuu-Token')
        self.assertIsNotNone(token)
        # Try and actiavte our account
        resp = self.client.get(url_for('activate', token=token),
                               follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Your account has now been activated', resp.data)

        # Try and activate the account again. We should get a 302 to /signin
        # and a flash message informing up that the account is already active
        resp = self.client.get(url_for('activate', token=token),
                               follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Your account has already been activated', resp.data)

        # Try and signup with the same user and ensure we get the correct resp
        # and error codes. We will also put mismatch passwords in just to test
        # that all forms throw the correct error
        resp = self.client.post(url_for('signup'), data={
                'username': 'test',
                'email': 'test@pjuu.com',
                'password': 'Password',
                'password2': 'PasswordPassword'
            }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        # Ensure there is an overall form error
        self.assertIn('Oh no! There are errors in your form', resp.data)
        # Ensure the form elements actually throw there own errors
        self.assertIn('User name already in use', resp.data)
        self.assertIn('E-mail address already in use', resp.data)
        self.assertIn('Passwords must match', resp.data)

        # Log in to Pjuu so that we can make sure we can not get back to signup
        resp = self.client.post(url_for('signin'), data={
                'username': 'test',
                'password': 'Password'
            }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        # We are now logged in lets try and go to signup and ensure we get
        # redirected back to feed
        resp = self.client.get(url_for('signup'))
        self.assertEqual(resp.status_code, 302)
        # Why we are logged in lets ensure we can't get to activate
        resp = self.client.get(url_for('activate', token=token))
        self.assertEqual(resp.status_code, 302)

        # Lets delete the account and then try and reactivate
        delete_account(1)
        resp = self.client.get(url_for('activate', token=token),
                               follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Invalid token', resp.data)

    def test_forgot_reset(self):
        """
        Test forgotten password and the password reset form.
        """
        # Test that we can GET the forgot page
        resp = self.client.get(url_for('forgot'))
        self.assertEqual(resp.status_code, 200)

        # Try and post data to the form even though we don't have a user.
        # This will work as the form will always return the same response
        # this is to stop users trying to recover random details
        resp = self.client.post(url_for('forgot'), data={
                'username': 'test'
            }, follow_redirects=True)
        # We should be redirect to login and a message flashed
        self.assertEqual(resp.status_code, 200)
        self.assertIn('If we\'ve found your account we\'ve', resp.data)
        # Let's make sure there is no X-Pjuu-Token header added as one should
        # not be generated for a non existant user
        self.assertIsNone(resp.headers.get('X-Pjuu-Token'))

        # Lets do this again but with a user (this is the only way to test
        # password resetting)
        self.assertEqual(create_user('test', 'test@pjuu.com', 'password'), 1)
        # Lets do the above test again but with this new user
        resp = self.client.post(url_for('forgot'), data={
                'username': 'test'
            }, follow_redirects=True)
        # We should be redirect to login and a message flashed
        self.assertEqual(resp.status_code, 200)
        self.assertIn('If we\'ve found your account we\'ve', resp.data)
        # This time we should have a token
        token = resp.headers.get('X-Pjuu-Token')
        self.assertIsNotNone(token)

        # Now we will try and change the password on our account
        # Lets just make sure we can get to the reset view with our token
        resp = self.client.get(url_for('reset', token=token))
        self.assertEqual(resp.status_code, 200)

        # Lets post to the view
        resp = self.client.post(url_for('reset', token=token), data={
                'password': 'Password',
                'password2': 'Password'
            }, follow_redirects=True)
        # This should redirect us back to the signin view as well as have
        # changed out password
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Your password has now been reset', resp.data)
        # We will just check we can log in with the new Password not password
        self.assertTrue(authenticate('test', 'Password'))
        # I know, I know this is tested in the backend buts let's make sure
        # we can't auth with the old password
        self.assertFalse(authenticate('test', 'password'))

        # Lets make sure the form tells us when we have filled it in wrong
        # Attempt to set a mis matching password
        resp = self.client.post(url_for('reset', token=token), data={
                'password': 'password',
                'password2': 'Password'
            }, follow_redirects = True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Oh no! There are errors in your form', resp.data)
        # Attempt to not even fill the form in
        resp = self.client.post(url_for('reset', token=token), data={},
                                follow_redirects = True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Oh no! There are errors in your form', resp.data)
        # This test is probably not compreshensive enough. Will add to it in
        # the near future. At least we can ensure the view works.

    def test_change_confirm_email(self):
        """
        Test changing your e-mail address from the frontend. This is the last
        function which uses Tokens.

        Note: We need to be logged in for this view to work.
        """
        # Try going to the view without being logged in
        resp = self.client.get(url_for('change_email'), follow_redirects=True)
        # We will just ensure we have been redirected to /signin
        self.assertEqual(resp.status_code, 200)
        # We should see a message saying we need to signin
        self.assertIn('You need to be logged in to view that', resp.data)

        # Let's create a user an login
        self.assertEqual(create_user('test', 'test@pjuu.com', 'password'), 1)
        # Activate the account
        self.assertTrue(activate(1))
        resp = self.client.post(url_for('signin'), data={
                'username': 'test',
                'password': 'password'
            }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        # Lets check to see that our current email is listed on the inital
        # settings page
        resp = self.client.get(url_for('settings_profile'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('test@pjuu.com', resp.data)

        # Lets double check we can get the change_email page and attempt to 
        # change our password.
        resp = self.client.get(url_for('change_email'))
        self.assertEqual(resp.status_code, 200)
        # Attempt to change our e-mail
        resp = self.client.post(url_for('change_email'), data={
                'password': 'password',
                'new_email': 'test1@pjuu.com'
            }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('We\'ve sent you an email, please confirm', resp.data)
        # Get the auth token
        token = resp.headers.get('X-Pjuu-Token')
        self.assertIsNotNone(token)

        # Confirm the email change
        resp = self.client.get(url_for('confirm_email', token=token),
                               follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('We\'ve updated your e-mail address', resp.data)

        # Let's ensure that our new e-mail appears on our profile page
        resp = self.client.get(url_for('settings_profile'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('test1@pjuu.com', resp.data)
        # Yey our email was updated

        # Lets just make sure we can't change our e-mail without a password
        resp = self.client.post(url_for('change_email'), data={
                'password': '',
                'new_email': 'test1@pjuu.com'
            }, follow_redirects=True)
        self.assertIn('Oh no! There are errors in your form', resp.data)

        # Lets make sure the email doesn't change until the confirmation is
        # checked
        resp = self.client.post(url_for('change_email'), data={
                'password': 'password',
                'new_email': 'test2@pjuu.com'
            }, follow_redirects=True)
        self.assertIn('We\'ve sent you an email, please confirm', resp.data)
        resp = self.client.get(url_for('settings_profile'))
        self.assertNotIn('test2@pjuu.com', resp.data)
        # Done for now :)

    def test_change_password(self):
        """
        Test that users can change their own passwords when they are logged in
        """
        # Try going to the view without being logged in
        resp = self.client.get(url_for('change_password'),
                               follow_redirects=True)
        # We will just ensure we have been redirected to /signin
        self.assertEqual(resp.status_code, 200)
        # We should see a message saying we need to signin
        self.assertIn('You need to be logged in to view that', resp.data)

        # Let's create a user an login
        self.assertEqual(create_user('test', 'test@pjuu.com', 'password'), 1)
        # Activate the account
        self.assertTrue(activate(1))
        # Log the user in
        resp = self.client.post(url_for('signin'), data={
                'username': 'test',
                'password': 'password'
            }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        # Goto the change password page
        resp = self.client.get(url_for('change_password'))
        self.assertEqual(resp.status_code, 200)

        # Attempt to change our password
        resp = self.client.post(url_for('change_password'), data={
                'password': 'password',
                'new_password': 'PASSWORD',
                'new_password2': 'PASSWORD'
            }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('We\'ve updated your password', resp.data)
        # Password was successfully changed

        # Lets try an change our password to one which is not a valid password
        resp = self.client.post(url_for('change_password'), data={
                'password': 'PASSWORD',
                'new_password': 'pass',
                'new_password2': 'pass'
            }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Password must be at least 6 characters long', resp.data)

        # Lets try an change our password but make them not match
        resp = self.client.post(url_for('change_password'), data={
                'password': 'PASSWORD',
                'new_password': 'password',
                'new_password2': 'passw0rd'
            }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Passwords must match', resp.data)

        # Lets try and change our pasword but provide a wrong current password
        resp = self.client.post(url_for('change_password'), data={
                'password': 'password',
                'new_password': 'password',
                'new_password2': 'password'
            }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Invalid password', resp.data)

    def test_delete_account(self):
        """
        Test deleting an account from the frontend
        """
        # Attempt to get to the delete_account view when not logged in
        resp = self.client.get(url_for('delete_account'),
                               follow_redirects=True)
        # We will just ensure we have been redirected to /signin
        self.assertEqual(resp.status_code, 200)
        # We should see a message saying we need to signin
        self.assertIn('You need to be logged in to view that', resp.data)

        # Let's create a user an login
        self.assertEqual(create_user('test', 'test@pjuu.com', 'password'), 1)
        # Activate the account
        self.assertTrue(activate(1))
        # Log the user in
        resp = self.client.post(url_for('signin'), data={
                'username': 'test',
                'password': 'password'
            }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        # Check that we can get to the delete_account page
        resp = self.client.get(url_for('delete_account'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('This action is irreversable', resp.data)

        # Attempy to delete account. We are going to do this the other way
        # round. We will try and do it with an invalid password etc first.
        resp = self.client.post(url_for('delete_account'), data={
                'password': 'PASSWORD'
            }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Oops! wrong password', resp.data)

        # That's all we can do to try and brake this. Let's delete our account
        resp = self.client.post(url_for('delete_account'), data={
                'password': 'password'
            }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Your account has been deleted', resp.data)

        # We are now back at signin. Let's check we can't login
        resp = self.client.post(url_for('signin'), data={
                'username': 'test',
                'password': 'password'
            })
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Invalid user name or password', resp.data)
        # Done
