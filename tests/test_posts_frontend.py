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
from pjuu.auth.backend import create_user, activate, get_user, mute
from pjuu.lib import keys as K
from pjuu.posts.backend import *
from pjuu.users.backend import follow_user, get_alerts
# Tests imports
from tests.helpers import BackendTestCase, FrontendTestCase


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
