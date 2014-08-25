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
from pjuu.lib import keys as K
from pjuu.lib.test_helpers import BackendTestCase, FrontendTestCase
from pjuu.auth.backend import create_user, activate, get_user, mute
from pjuu.users.backend import follow_user
from .backend import *


###############################################################################
# BACKEND #####################################################################
###############################################################################


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


###############################################################################
# FRONTEND ####################################################################
###############################################################################


class FrontendTests(FrontendTestCase):
    """
    This test case will test all the posts subpackages; views, decorators
    and forms
    """

    def test_post(self):
        """
        Test that we can post too Pjuu.
        """
        # Lets ensure we can't GET the /post endpoint
        # You should not be able to GET this resouce but you will not see this
        # until you are signed in. This should simply redirect us to login
        resp = self.client.get(url_for('post'))
        self.assertEqual(resp.status_code, 302)

        # Lets ensure we can't POST to /post when logged out
        # As above we should simply be redirected
        resp = self.client.post(url_for('post'), data={
            'body': 'A post'
        })
        self.assertEqual(resp.status_code, 302)

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

        # We are now logged in :) Let's ensure we can't GET the /post endpoint
        resp = self.client.get(url_for('post'))
        self.assertEqual(resp.status_code, 405)

        # Lets post a test post
        # Because we are not passing a next query param we will be redirected
        # to /test (users profile) after this post
        resp = self.client.post(url_for('post'), data={
            'body': 'A new post'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        # Let's ensure our new post appears in the output
        self.assertIn('A new post', resp.data)
        # We should be on the posts view as we did not pass a next qs
        self.assertIn('<h1>Create new post</h1>', resp.data)

        # Let's post again but this time lets redirect ourselves back to feed.
        # We will ensure both posts exist in the feed
        resp = self.client.post(url_for('post', next=url_for('feed')), data={
            'body': 'A second post'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        # Let's ensure both posts are their
        self.assertIn('A new post', resp.data)
        self.assertIn('A second post', resp.data)

        # The post endpoint also handles populating followers feeds. We will
        # create a couple of users (in the backend, we will not test the
        # frontend here).
        self.assertEqual(create_user('test2', 'test2@pjuu.com', 'password'), 2)
        self.assertTrue(activate(2))
        self.assertTrue(follow_user(2, 1))
        self.assertEqual(create_user('test3', 'test3@pjuu.com', 'password'), 3)
        self.assertTrue(activate(3))
        self.assertTrue(follow_user(3, 1))

        # Create a post as user 1, we will then log out and ensure these posts
        # appear in the other users lists
        resp = self.client.post(url_for('post', next=url_for('feed')), data={
            'body': 'Hello followers'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        # Let's ensure all posts are their
        self.assertIn('A new post', resp.data)
        self.assertIn('A second post', resp.data)
        self.assertIn('Hello followers', resp.data)
        # Let's ensure the post form is their
        self.assertIn('<h1>Create new post</h1>', resp.data)

        # We are using the test client so lets log out properly
        self.client.get(url_for('signout'))

        # Log in as test2 and ensure the post is in their feed
        resp = self.client.post(url_for('signin'), data={
            'username': 'test2',
            'password': 'password'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Hello followers', resp.data)
        # Log out
        self.client.get(url_for('signout'))

        # Log in as test3 and ensure the post in their feed
        resp = self.client.post(url_for('signin'), data={
            'username': 'test3',
            'password': 'password'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Hello followers', resp.data)
        # Log out
        self.client.get(url_for('signout'))

        # Sign back in as out test user so that we can keep testing
        resp = self.client.post(url_for('signin'), data={
            'username': 'test',
            'password': 'password'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        # Back to testing. Let's ensure that users can post unicode text
        # I copied this Chinese text from a header file on my Mac. I do not
        # know what it means, I just need the characters
        resp = self.client.post(url_for('post', next=url_for('feed')), data={
            'body': '光铸钥匙'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        # Let's ensure all posts are their
        self.assertIn('A new post', resp.data)
        self.assertIn('A second post', resp.data)
        self.assertIn('Hello followers', resp.data)
        self.assertIn('光铸钥匙', resp.data)

        # Check that a muted user can not create a post
        # Mute out user
        self.assertTrue(mute(1))
        resp = self.client.post(url_for('post', next=url_for('feed')), data={
            'body': 'Muting test'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        # Let's ensure the warning is there
        self.assertIn('You have been silenced!', resp.data)
        self.assertNotIn('Muting test', resp.data)
        # Un-mute the user and try and post the same thing
        self.assertTrue(mute(1, False))
        resp = self.client.post(url_for('post', next=url_for('feed')), data={
            'body': 'Muting test'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        # Let's ensure the warning is there
        self.assertNotIn('You have been silenced!', resp.data)
        self.assertIn('Muting test', resp.data)

        # Done for now

    def test_comment(self):
        """
        Test commenting on a post. This is a lot simpler than making a post
        """
        # We can not test getting to a comment as we need a post and a user
        # for this too happen

        # Let's create a user and login
        self.assertEqual(create_user('test', 'test@pjuu.com', 'password'), 1)
        # Activate the account
        self.assertTrue(activate(1))
        # Log the user in
        resp = self.client.post(url_for('signin'), data={
            'username': 'test',
            'password': 'password'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        # Create a post to comment on we will do this in the backend to get
        # the pid
        self.assertEqual(create_post(1, 'Test post'), 1)

        # Lets attempt to GET to the comment view. Should fail we can only POST
        # like we can to /post
        resp = self.client.get(url_for('comment', username='test', pid=1))
        # Method not allowed
        self.assertEqual(resp.status_code, 405)

        # Lets post a comment and follow the redirects this should take us to
        # the comment page
        resp = self.client.post(url_for('comment', username='test', pid=1),
                                data={'body': 'Test comment'},
                                follow_redirects=True)
        # Lets check that we can see the comment
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Test comment', resp.data)
        # Lets also make sure the form is visible on the page
        self.assertIn('<h1>Make a comment</h1>', resp.data)

        # Lets signout
        resp = self.client.get(url_for('signout'))
        self.assertEqual(resp.status_code, 302)

        # Lets create another test user and ensure that they can see the
        # comment
        self.assertEqual(create_user('test2', 'test2@pjuu.com', 'password'), 2)
        # Activate the account
        self.assertTrue(activate(2))
        # Log the user in
        resp = self.client.post(url_for('signin'), data={
            'username': 'test2',
            'password': 'password'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        # Lets just check that we can see the comment if we go to the view_post
        # view
        resp = self.client.get(url_for('view_post', username='test', pid=1))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Test comment', resp.data)

        # Lets comment ourselves
        resp = self.client.post(url_for('comment', username='test', pid=1),
                                data={'body': 'Comment 2'},
                                follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        # Check that the 2 comments exist
        self.assertIn('Test comment', resp.data)
        self.assertIn('Comment 2', resp.data)

        # Lets check we can not comment if we are muted
        self.assertTrue(mute(2))
        resp = self.client.post(url_for('comment', username='test', pid=1),
                                data={'body': 'Muting test'},
                                follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        # Check that the comment was never posted
        self.assertIn('You have been silenced!', resp.data)
        self.assertNotIn('Muting test', resp.data)

        # Reverse the muting and test again
        self.assertTrue(mute(2, False))
        resp = self.client.post(url_for('comment', username='test', pid=1),
                                data={'body': 'Muting test'},
                                follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        # Check that the comment was never posted
        self.assertNotIn('You have been silenced!', resp.data)
        self.assertIn('Muting test', resp.data)

        # Lets signout
        resp = self.client.get(url_for('signout'))
        self.assertEqual(resp.status_code, 302)

        # Done for now

    def test_up_down_vote(self):
        """
        Test voting up and down on both comments and posts
        """
        # Create two users to test this. This is what we need to check this.
        self.assertEqual(create_user('test1', 'test1@pjuu.com', 'password'), 1)
        self.assertEqual(create_user('test2', 'test2@pjuu.com', 'password'), 2)
        # Activate the accounts
        self.assertTrue(activate(1))
        self.assertTrue(activate(2))

        # Create a post as the first user
        self.assertEqual(create_post(1, 'Post user 1'), 1)
        # Create a post as user 2
        self.assertEqual(create_post(2, 'Post user 2'), 2)
        # Create comment as user two on user 1's comment
        self.assertEqual(create_comment(2, 1, 'Comment user 2'), 1)

        # Create a second post for user 2 we will use this to ensure we can't
        # vote on out own post
        self.assertEqual(create_post(1, 'Second post user 1'), 3)
        # We will have 1 comment from user 1 on this post by user 1 to ensure
        # that we can't vote on either
        self.assertEqual(create_comment(1, 3, 'Comment user 1'), 2)

        # We will now actually test the frontend
        # Log in as user 1
        resp = self.client.post(url_for('signin'), data={
            'username': 'test1',
            'password': 'password'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        # Lets ensure both vote links are there
        resp = self.client.get(url_for('view_post', username='test2', pid=2))
        self.assertIn('up_arrow.png', resp.data)
        self.assertIn('down_arrow.png', resp.data)

        # Visit user 2's comment and UPVOTE that
        resp = self.client.get(url_for('upvote', username='test2', pid=2),
                               follow_redirects=True)
        # We should now be at the posts page
        self.assertEqual(resp.status_code, 200)
        # Now that we have voted we should only see the arrow pointing to what
        # we voted. Check for up_arrow and ensure down_arrow is not there
        self.assertIn('up_arrow.png', resp.data)
        self.assertNotIn('down_arrow.png', resp.data)

        # Let's try and vote on that post again
        resp = self.client.get(url_for('upvote', username='test2', pid=2),
                               follow_redirects=True)
        # We should now be at the posts page
        self.assertEqual(resp.status_code, 200)
        # Now that we have voted we should only see the arrow pointing to what
        # we voted. Check for up_arrow and ensure down_arrow is not there
        self.assertIn('You have already voted on this post', resp.data)

        # Visit our own post and ensure that user 2s comment is there
        # There will be only one set of arrows as we can't vote on our own post
        # we will check that part later on
        resp = self.client.get(url_for('view_post', username='test1', pid=1))
        self.assertIn('Comment user 2', resp.data)
        self.assertIn('up_arrow.png', resp.data)
        self.assertIn('down_arrow.png', resp.data)

        # Down vote the users comment (it's nothing personal test2 :P)
        resp = self.client.get(url_for('downvote', username='test1', pid=1,
                               cid=1), follow_redirects=True)
        self.assertIn('down_arrow.png', resp.data)
        self.assertNotIn('up_arrow.png', resp.data)

        # Lets check that we can't vote on this comment again
        resp = self.client.get(url_for('downvote', username='test1', pid=1,
                               cid=1), follow_redirects=True)
        self.assertIn('You have already voted on this post', resp.data)

        # Now lets double check we can't vote on our own comments or posts
        # We will visit post 3 first and ensure there is no buttons being shown
        resp = self.client.get(url_for('view_post', username='test1', pid=3))
        self.assertNotIn('up_arrow.png', resp.data)
        self.assertNotIn('down_arrow.png', resp.data)
        # Check that the comment is there
        self.assertIn('Comment user 1', resp.data)

        # Lets ensure we can't vote on either the comment or the post
        resp = self.client.get(url_for('upvote', username='test1', pid=3),
                               follow_redirects=True)
        self.assertIn('You can not vote on your own posts', resp.data)

        resp = self.client.get(url_for('upvote', username='test1', pid=3,
                               cid=2), follow_redirects=True)
        self.assertIn('You can not vote on your own posts', resp.data)

        # Try and vote on a comment or post that does not exist
        # Vote on a post
        resp = self.client.get(url_for('upvote', username='test1', pid=65),
                               follow_redirects=True)
        self.assertEqual(resp.status_code, 404)
        # Vote on a comment
        resp = self.client.get(url_for('downvote', username='test1', pid=3,
                               cid=4532), follow_redirects=True)
        self.assertEqual(resp.status_code, 404)
        # Vote on a post when the user doesn't even exists
        resp = self.client.get(url_for('downvote', username='test524', pid=3,
                               cid=4532), follow_redirects=True)
        self.assertEqual(resp.status_code, 404)

        # Let's ensure a logged out user can not perform any of these actions
        # Signout
        self.client.get(url_for('signout'), follow_redirects=True)
        # We are at the signin page
        # Vote on a post
        resp = self.client.get(url_for('upvote', username='test1', pid=3),
                               follow_redirects=True)
        self.assertIn('You need to be logged in to view that', resp.data)
        # Vote on a comment
        resp = self.client.get(url_for('downvote', username='test1', pid=3,
                               cid=2), follow_redirects=True)
        self.assertIn('You need to be logged in to view that', resp.data)
        # Done for now

    def test_delete_post(self):
        """
        Let's test the ability to delete posts and comments
        """
        # Create 3 users for this
        self.assertEqual(create_user('test1', 'test1@pjuu.com', 'Password'), 1)
        self.assertEqual(create_user('test2', 'test2@pjuu.com', 'Password'), 2)
        self.assertEqual(create_user('test3', 'test3@pjuu.com', 'Password'), 3)
        # Activate the accounts
        self.assertTrue(activate(1))
        self.assertTrue(activate(2))
        self.assertTrue(activate(3))
        # Create a test post as each user
        self.assertEqual(create_post(1, 'Test post, user 1'), 1)
        self.assertEqual(create_post(2, 'Test post, user 2'), 2)
        self.assertEqual(create_post(3, 'Test post, user 3'), 3)

        # Log in as user 1
        resp = self.client.post(url_for('signin'), data={
            'username': 'test1',
            'password': 'Password'
        }, follow_redirects=True)
        self.assertIn('<h1>Feed</h1>', resp.data)

        # Visit our own post and ensure the delete button is there
        resp = self.client.get(url_for('view_post', username='test1', pid=1))
        self.assertIn('<div class="delete">X</div>', resp.data)
        # Visit test2's post and ensure button is not there
        resp = self.client.get(url_for('view_post', username='test2', pid=2))
        self.assertNotIn('<div class="delete">X</div>', resp.data)

        # Try and delete user two's comment this should fail
        resp = self.client.get(url_for('delete_post', username='test2', pid=2))
        self.assertEqual(resp.status_code, 403)
        # Ensure the post is still actuall there
        resp = self.client.get(url_for('view_post', username='test2', pid=2))
        self.assertIn('Test post, user 2', resp.data)

        # Let's delete our own post
        resp = self.client.get(url_for('delete_post', username='test1', pid=1),
                               follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Post has been deleted along with all comments',
                      resp.data)
        # Let's ensure the post no longer exists
        resp = self.client.get(url_for('view_post', username='test1', pid=1))
        self.assertEqual(resp.status_code, 404)

        # Create a comment for each user on the only remaining post (2)
        self.assertEqual(create_comment(1, 2, 'Test comment, user 1'), 1)
        self.assertEqual(create_comment(2, 2, 'Test comment, user 2'), 2)
        self.assertEqual(create_comment(3, 2, 'Test comment, user 3'), 3)

        # Visit the post ensure the comments are there and there is a delete
        # button, there should only be one as we are user 1 :)
        resp = self.client.get(url_for('view_post', username='test2', pid=2))
        # Make sure both comments are there
        self.assertIn('Test comment, user 1', resp.data)
        self.assertIn('Test comment, user 2', resp.data)
        self.assertIn('Test comment, user 3', resp.data)

        # Let's delete are own comment
        resp = self.client.get(url_for('delete_post', username='test2', pid=2,
                                       cid=1), follow_redirects=True)
        # Check we have confirmation
        self.assertIn('Comment has been deleted', resp.data)
        # Lets check that comment 2 is there
        self.assertIn('Test comment, user 2', resp.data)
        self.assertIn('Test comment, user 3', resp.data)
        # Lets ensure our comment is gone
        self.assertNotIn('Test comment, user 1', resp.data)

        # Attempt to delete user 2's comment. This should fail with a 403
        # as we are neither the comment author nor the post author
        resp = self.client.get(url_for('delete_post', username='test2', pid=2,
                                       cid=2), follow_redirects=True)
        # Let's check we got the error
        self.assertEqual(resp.status_code, 403)

        # Attempt to delete user 2's post we should receive a 403
        resp = self.client.get(url_for('delete_post', username='test2', pid=2,
                                       cid=2))
        self.assertEqual(resp.status_code, 403)

        # Let's just ensure the comment wasn't deleted
        resp = self.client.get(url_for('view_post', username='test2', pid=2))
        self.assertIn('Test comment, user 2', resp.data)

        # Log out as user 1
        self.client.get(url_for('signout'))

        # Log in as user test2 and delete user test3's comment
        # Test2 is the post author so they should be able to delete not their
        # own comments

        resp = self.client.post(url_for('signin'), data={
            'username': 'test2',
            'password': 'Password'
        }, follow_redirects=True)
        self.assertIn('<h1>Feed</h1>', resp.data)

        # Goto test2s post
        resp = self.client.get(url_for('view_post', username='test2', pid=2))
        # Ensure test2 and test3s comments are there but not test1
        self.assertIn('Test comment, user 2', resp.data)
        self.assertIn('Test comment, user 3', resp.data)
        self.assertNotIn('Test comment, user 1', resp.data)

        # No need to test that test2 can delete there own post as we have
        # tested this already with test1
        resp = self.client.get(url_for('delete_post', username='test2', pid=2,
                                       cid=3), follow_redirects=True)
        # Check we have confirmation
        self.assertIn('Comment has been deleted', resp.data)
        # Lets check that comment 2 is there
        self.assertIn('Test comment, user 2', resp.data)
        # Lets ensure our comment is gone
        self.assertNotIn('Test comment, user 1', resp.data)
        self.assertNotIn('Test comment, user 3', resp.data)

        # Done for now

    def test_subscriptions(self):
        """
        Test that subscriptions work through the frontend.

        This mainly just tests unsubscribe button as the rest is tested in the
        backend.
        """
        # Create 3 users for this
        self.assertEqual(create_user('test1', 'test1@pjuu.com', 'Password'), 1)
        self.assertEqual(create_user('test2', 'test2@pjuu.com', 'Password'), 2)
        self.assertEqual(create_user('test3', 'test3@pjuu.com', 'Password'), 3)
        # Activate the accounts
        self.assertTrue(activate(1))
        self.assertTrue(activate(2))
        self.assertTrue(activate(3))

        # Create a test post as test1
        self.assertEqual(create_post(1, 'Test post, user 1'), 1)

        # Login as test1
        # Don't bother testing this AGAIN
        self.client.post(url_for('signin'), data={
            'username': 'test1',
            'password': 'Password'
        })

        # Visit the posts page and ensure unsubscribe button is there
        # We should have been subscribed when create_post was run above
        resp = self.client.get(url_for('view_post', username='test1', pid=1))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('<div class="action-button unsubscribe">', resp.data)

        # Unsubscribe via the frontend and ensure the button is removed and
        # we get a flash message
        resp = self.client.get(url_for('unsubscribe', username='test1', pid=1),
                               follow_redirects=True)
        self.assertIn('You have been unsubscribed from this post', resp.data)
        self.assertNotIn('<div class="action-button unsubscribe">', resp.data)

        # Done for now. This proves that unsubscribe works and the backend test
        # proves that all methods being subscibed work :D
