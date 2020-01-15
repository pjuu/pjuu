# -*- coding: utf8 -*-

"""Post frontend tests.

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2020 Joe Doherty

"""

import io
import json
from time import sleep

from flask import url_for

import pjuu  # Used to monkey patch VOTE_TIMEOUT
from pjuu import mongo as m
from pjuu.auth.backend import create_account, activate, mute, bite
from pjuu.lib import keys as k
from pjuu.posts.backend import (create_post, get_post, MAX_POST_LENGTH,
                                has_flagged, flag_post)
from pjuu.users.backend import (
    follow_user, update_profile_settings, approve_user
)
from pjuu.users.views import millify_filter, timeify_filter

from tests import FrontendTestCase


class PostFrontendTests(FrontendTestCase):
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
        resp = self.client.get(url_for('posts.post'))
        self.assertEqual(resp.status_code, 302)

        # Lets ensure we can't POST to /post when logged out
        # As above we should simply be redirected
        resp = self.client.post(url_for('posts.post'), data={
            'body': 'Test post'
        })
        self.assertEqual(resp.status_code, 302)

        # Let's create a user an login
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        # Activate the account
        self.assertTrue(activate(user1))
        # # Log the user in
        resp = self.client.post(url_for('auth.signin'), data={
            'username': 'user1',
            'password': 'Password'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        # We are now logged in :) Let's ensure we can't GET the /post endpoint
        resp = self.client.get(url_for('posts.post'))
        self.assertEqual(resp.status_code, 405)

        # Lets post a test post
        # Because we are not passing a next query param we will be redirected
        # to /test (users profile) after this post
        resp = self.client.post(url_for('posts.post'), data={
            'body': 'Test post'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        # Let's ensure our new post appears in the output
        self.assertIn('Test post', resp.get_data(as_text=True))
        # We should be on the posts view as we did not pass a next qs
        self.assertIn('<!-- author post -->', resp.get_data(as_text=True))

        # Let's post again but this time lets redirect ourselves back to feed.
        # We will ensure both posts exist in the feed
        resp = self.client.post(url_for('posts.post',
                                        next=url_for('users.feed')),
                                data={
            'body': 'Second test post'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        # Let's ensure both posts are their
        self.assertIn('Test post', resp.get_data(as_text=True))
        self.assertIn('Second test post', resp.get_data(as_text=True))

        # The post endpoint also handles populating followers feeds. We will
        # create a couple of users (in the backend, we will not test the
        # frontend here).
        user2 = create_account('user2', 'user2@pjuu.com', 'Password')
        activate(user2)
        follow_user(user2, user1)

        user3 = create_account('user3', 'user3@pjuu.com', 'Password')
        activate(user3)
        follow_user(user3, user1)

        # Create a post as user 1, we will then log out and ensure these posts
        # appear in the other users lists
        resp = self.client.post(url_for('posts.post',
                                        next=url_for('users.feed')),
                                data={
            'body': 'Hello followers'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        # Let's ensure all posts are their
        self.assertIn('Test post', resp.get_data(as_text=True))
        self.assertIn('Second test post', resp.get_data(as_text=True))
        self.assertIn('Hello followers', resp.get_data(as_text=True))
        # Let's ensure the post form is their
        self.assertIn('<!-- author post -->', resp.get_data(as_text=True))

        # We are using the test client so lets log out properly
        self.client.get(url_for('auth.signout'))

        # Log in as test2 and ensure the post is in their feed
        resp = self.client.post(url_for('auth.signin'), data={
            'username': 'user2',
            'password': 'Password'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Hello followers', resp.get_data(as_text=True))
        # Log out
        self.client.get(url_for('auth.signout'))

        # Log in as test3 and ensure the post in their feed
        resp = self.client.post(url_for('auth.signin'), data={
            'username': 'user3',
            'password': 'Password'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Hello followers', resp.get_data(as_text=True))
        # Log out
        self.client.get(url_for('auth.signout'))

        # Sign back in as user1 so that we can keep testing
        resp = self.client.post(url_for('auth.signin'), data={
            'username': 'user1',
            'password': 'Password'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        # Back to testing. Let's ensure that users can post unicode text
        # I copied this Chinese text from a header file on my Mac. I do not
        # know what it means, I just need the characters
        resp = self.client.post(url_for('posts.post',
                                        next=url_for('users.feed')),
                                data={
            'body': '光铸钥匙'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        # Let's ensure all posts are their
        self.assertIn('Test post', resp.get_data(as_text=True))
        self.assertIn('Second test post', resp.get_data(as_text=True))
        self.assertIn('Hello followers', resp.get_data(as_text=True))
        self.assertIn('光铸钥匙', resp.get_data(as_text=True))

        # Check that a muted user can not create a post
        # Mute out user
        mute(user1)
        resp = self.client.post(url_for('posts.post',
                                        next=url_for('users.feed')),
                                data={
            'body': 'Muting test'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        # Let's ensure the warning is there
        self.assertIn('You have been silenced!', resp.get_data(as_text=True))
        self.assertNotIn('Muting test', resp.get_data(as_text=True))
        # Un-mute the user and try and post the same thing
        self.assertTrue(mute(user1, False))
        resp = self.client.post(url_for('posts.post',
                                        next=url_for('users.feed')),
                                data={
            'body': 'Muting test'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        # Let's ensure the warning is there
        self.assertNotIn('You have been silenced!',
                         resp.get_data(as_text=True))
        self.assertIn('Muting test', resp.get_data(as_text=True))

        # Try and post to many characters
        resp = self.client.post(url_for('posts.post',
                                        next=url_for('users.feed')),
                                data={
            'body': ('P' * (MAX_POST_LENGTH + 1))
        }, follow_redirects=True)
        self.assertIn('Posts can not be larger than '
                      '{0} characters'.format(MAX_POST_LENGTH),
                      resp.get_data(as_text=True))

        # Test that we can post 500 unicode characters
        resp = self.client.post(url_for('posts.post',
                                        next=url_for('users.feed')),
                                data={
            'body': ('光' * (MAX_POST_LENGTH))
        }, follow_redirects=True)
        self.assertNotIn('Posts can not be larger than '
                         '{0} characters'.format(MAX_POST_LENGTH),
                         resp.get_data(as_text=True))

        # Test that we can not post more than MAX_POST_LENGTH unicode
        # characters
        resp = self.client.post(url_for('posts.post',
                                        next=url_for('users.feed')),
                                data={
            'body': ('光' * (MAX_POST_LENGTH + 1))
        }, follow_redirects=True)
        self.assertIn('Posts can not be larger than '
                      '{0} characters'.format(MAX_POST_LENGTH),
                      resp.get_data(as_text=True))

        # Ensure that posting an image with no text allows it
        image = io.BytesIO(
            open('tests/upload_test_files/otter.jpg', 'rb').read())
        resp = self.client.post(
            url_for('posts.post'),
            data={
                'body': '',
                'upload': (image, 'otter.jpg')
            },
            follow_redirects=True
        )
        self.assertEqual(resp.status_code, 200)

        # Test posting with an image
        image = io.BytesIO(
            open('tests/upload_test_files/otter.jpg', 'rb').read())
        resp = self.client.post(
            url_for('posts.post'),
            data={
                'body': 'Test upload',
                'upload': (image, 'otter.jpg')
            },
            follow_redirects=True
        )

        self.assertEqual(resp.status_code, 200)

        # Goto the users feed an ensure the post is there
        resp = self.client.get(url_for('users.feed'))
        self.assertEqual(resp.status_code, 200)

        # So that we can check the data is in the templates, upload a post
        # in the backend and ensure it appears where it should
        image = io.BytesIO(
            open('tests/upload_test_files/otter.png', 'rb').read())
        post1 = create_post(user1, 'user1', 'Test post', upload=image)
        self.assertIsNotNone(post1)
        post = get_post(post1)
        resp = self.client.get(url_for('users.feed'))
        self.assertIn('<!-- upload:post:{} -->'.format(post1),
                      resp.get_data(as_text=True))
        self.assertIn('<img src="{}"/>'.format(
            url_for('posts.get_upload', filename=post.get('upload'))),
                      resp.get_data(as_text=True))

        # Although the below belongs in `test_view_post` we are just going to
        # check it here for simplicity
        resp = self.client.get(url_for('posts.view_post', username='user1',
                                       post_id=post1))
        self.assertIn('<!-- upload:post:{} -->'.format(post1),
                      resp.get_data(as_text=True))
        self.assertIn(
            '<img src="{}"/>'.format(url_for('posts.get_upload',
                                             filename=post.get('upload'))),
            resp.get_data(as_text=True))

        # Test posting with no data
        resp = self.client.post(url_for('posts.post',
                                        next=url_for('users.feed')),
                                data={
            'body': ''
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Sorry. A message or an image is required.',
                      resp.get_data(as_text=True))

    def test_posts_lines(self):
        """Ensure posts are truncated to `LINE_CAP` on feeds and profiles"""
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        activate(user1)
        self.client.post(url_for('auth.signin'), data={
            'username': 'user1',
            'password': 'Password'
        }, follow_redirects=True)

        resp = self.client.post(url_for('posts.post',
                                        next=url_for('users.feed')),
                                data={
            'body': '\n'.join([
                'Line 0',
                'Line 1',
                'Line 2',
                'Line 3',
                'Line 4',
                'Line 5',
                'Line 6',
                'Line 7',
                'Line 8',
                'Line 9',
            ])
        }, follow_redirects=True)

        self.assertIn('Line 0<br/>', resp.get_data(as_text=True))
        # The last line wil NOT have a <br/> attached.
        self.assertIn('Line 4', resp.get_data(as_text=True))
        self.assertIn('Read more ...', resp.get_data(as_text=True))

        self.assertNotIn('Line 5', resp.get_data(as_text=True))
        self.assertNotIn('Line 9', resp.get_data(as_text=True))

        # Ensure the same thing happens on the users profile.
        resp = self.client.get(url_for('users.profile', username='user1'))

        self.assertIn('Line 0<br/>', resp.get_data(as_text=True))
        # The last line wil NOT have a <br/> attached.
        self.assertIn('Line 4', resp.get_data(as_text=True))
        self.assertIn('Read more ...', resp.get_data(as_text=True))

        self.assertNotIn('Line 5', resp.get_data(as_text=True))
        self.assertNotIn('Line 9', resp.get_data(as_text=True))

        # Ensure the post shows in full on the actual post page
        post1 = create_post(user1, 'user1', '\n'.join([
            'Line 0',
            'Line 1',
            'Line 2',
            'Line 3',
            'Line 4',
            'Line 5',
            'Line 6',
            'Line 7',
            'Line 8',
            'Line 9',
        ]))

        resp = self.client.get(url_for('posts.view_post', username='user1',
                                       post_id=post1))

        self.assertIn('Line 0<br/>', resp.get_data(as_text=True))
        self.assertIn('Line 4<br/>', resp.get_data(as_text=True))
        self.assertIn('Line 5<br/>', resp.get_data(as_text=True))
        # Last item has no <br/>
        self.assertIn('Line 9', resp.get_data(as_text=True))

        self.assertNotIn('Read more ...', resp.get_data(as_text=True))

        self.assertEqual(resp.status_code, 200)

    def test_hide_feed_images(self):
        """"""
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        activate(user1)
        # Log the user in
        resp = self.client.post(url_for('auth.signin'), data={
            'username': 'user1',
            'password': 'Password'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        # Disable feed images
        update_profile_settings(user1, hide_feed_images=True)

        # Upload another image
        image = io.BytesIO(
            open('tests/upload_test_files/otter.png', 'rb').read())
        post1 = create_post(user1, 'user1', 'Test post', upload=image)
        self.assertIsNotNone(post1)

        post = get_post(post1)
        resp = self.client.get(url_for('users.feed'))
        self.assertIn('<!-- upload:post:{} -->'.format(post1),
                      resp.get_data(as_text=True))
        self.assertNotIn('<img src="{}"/>'.format(
            url_for('posts.get_upload', filename=post.get('upload'))),
                         resp.get_data(as_text=True))
        self.assertIn('<!-- upload:hidden:{} -->'.format(post1),
                      resp.get_data(as_text=True))

    def test_get_upload(self):
        """Tests the simple wrapper around ``lib.uploads.get_upload``

        """
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        activate(user1)

        # Create the post with an upload to get
        image = io.BytesIO(
            open('tests/upload_test_files/otter.jpg', 'rb').read())
        post1 = create_post(user1, 'user1', 'Test post', upload=image)
        self.assertIsNotNone(post1)

        post = get_post(post1)

        # You can download an upload when you are NOT logged in
        # This allows web tier caching
        resp = self.client.get(url_for('posts.get_upload',
                                       filename=post.get('upload')))
        self.assertEqual(resp.status_code, 200)

        # Log in as user1 and get the upload
        resp = self.client.post(url_for('auth.signin'), data={
            'username': 'user1',
            'password': 'Password'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        resp = self.client.get(url_for('posts.get_upload',
                                       filename=post.get('upload')))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers['Content-Type'], 'image/png')

    def test_view_post(self):
        """
        Similar to above but check the same for the view_post page. This is
        mainly intended to check that comments render correctly
        """
        # Create two test users
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        user2 = create_account('user2', 'user2@pjuu.com', 'Password')
        activate(user1)
        activate(user2)

        post1 = create_post(user1, 'user1', 'Test post')

        # Ensure we can't hit the endpoing
        # We should be able to see the endpoint due to privacy changes.
        resp = self.client.get(url_for('posts.view_post', username='user1',
                                       post_id=post1),
                               follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Test post', resp.get_data(as_text=True))

        # Sign in
        self.client.post(url_for('auth.signin'), data={
            'username': 'user1',
            'password': 'Password'
        }, follow_redirects=True)

        # Ensure that we can now see the endpoint
        resp = self.client.get(url_for('posts.view_post', username='user1',
                                       post_id=post1),
                               follow_redirects=True)
        # Use the testing tags to ensure everything is rendered
        self.assertIn('<!-- view:post:{} -->'.format(post1),
                      resp.get_data(as_text=True))
        self.assertIn('Test post', resp.get_data(as_text=True))
        # Ensure the comment form is present
        self.assertIn('<!-- author reply -->', resp.get_data(as_text=True))

        # Create a comment on the post
        comment1 = create_post(user1, 'user1', 'Test comment 1', post1)

        # Get the view again
        resp = self.client.get(url_for('posts.view_post', username='user1',
                                       post_id=post1),
                               follow_redirects=True)

        self.assertIn('<!-- list:reply:{} -->'.format(comment1),
                      resp.get_data(as_text=True))
        self.assertIn('Test comment 1', resp.get_data(as_text=True))

        # Let's logout and log in as test2
        self.client.get(url_for('auth.signout'))
        self.client.post(url_for('auth.signin'), data={
            'username': 'user2',
            'password': 'Password'
        })
        # Check that we can see the comment
        resp = self.client.get(url_for('posts.view_post', username='user1',
                                       post_id=post1),
                               follow_redirects=True)
        self.assertIn('<!-- view:post:{} -->'.format(post1),
                      resp.get_data(as_text=True))
        self.assertIn('Test post', resp.get_data(as_text=True))
        self.assertIn('<!-- list:reply:{} -->'.format(comment1),
                      resp.get_data(as_text=True))
        self.assertIn('Test comment', resp.get_data(as_text=True))

        comment2 = create_post(user2, 'user2', 'Test comment 2', post1)

        # Get the view again
        resp = self.client.get(url_for('posts.view_post', username='user1',
                                       post_id=post1),
                               follow_redirects=True)

        self.assertIn('<!-- list:reply:{} -->'.format(comment2),
                      resp.get_data(as_text=True))
        self.assertIn('Test comment 2', resp.get_data(as_text=True))
        # Done for now

        # Attempt to view_post on a reply. Shouldn't work
        resp = self.client.get(url_for('posts.view_post', username='user2',
                                       post_id=comment2))
        self.assertEqual(resp.status_code, 404)

    def test_reply_sort_order(self):
        """Ensure that changing the reply sort order yields the desired
        effect."""
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        activate(user1)

        # Sign in

        post1 = create_post(user1, 'user1', 'Test post')

        for i in range(100):
            create_post(user1, 'user1', 'Reply {}'.format(i), post1)

        # Test reply sort order for logged out users
        resp = self.client.get(url_for('posts.view_post', username='user1',
                                       post_id=post1),
                               follow_redirects=True)

        self.assertIn('fa-sort-numeric-asc', resp.get_data(as_text=True))

        resp = self.client.get(url_for('posts.view_post', username='user1',
                                       post_id=post1, sort=-1),
                               follow_redirects=True)

        for i in range(99, 75, -1):
            self.assertIn('Reply {}'.format(i), resp.get_data(as_text=True))

        resp = self.client.get(url_for('posts.view_post', username='user1',
                                       post_id=post1, sort=1),
                               follow_redirects=True)

        # Check reverse-chronological sort link is present
        self.assertIn('fa-sort-numeric-desc', resp.get_data(as_text=True))

        for i in range(24):
            self.assertIn('Reply {}'.format(i), resp.get_data(as_text=True))

        # Ensure an invalid sort order is treated correctly.
        # Default is reverse chronological
        resp = self.client.get(url_for('posts.view_post', username='user1',
                                       post_id=post1, sort="bob"),
                               follow_redirects=True)

        for i in range(99, 75, -1):
            self.assertIn('Reply {}'.format(i), resp.get_data(as_text=True))

        self.client.post(url_for('auth.signin'), data={
            'username': 'user1',
            'password': 'Password'
        }, follow_redirects=True)

        resp = self.client.get(url_for('posts.view_post', username='user1',
                                       post_id=post1),
                               follow_redirects=True)

        # Check chronological sort link is present
        self.assertIn('fa-sort-numeric-asc', resp.get_data(as_text=True))

        for i in range(99, 75, -1):
            self.assertIn('Reply {}'.format(i), resp.get_data(as_text=True))

        # Explicit default sort
        resp = self.client.get(url_for('posts.view_post', username='user1',
                                       post_id=post1, sort=-1),
                               follow_redirects=True)

        for i in range(99, 75, -1):
            self.assertIn('Reply {}'.format(i), resp.get_data(as_text=True))

        # Explicit chronological sort
        resp = self.client.get(url_for('posts.view_post', username='user1',
                                       post_id=post1, sort=1),
                               follow_redirects=True)

        # Check reverse-chronological sort link is present
        self.assertIn('fa-sort-numeric-desc', resp.get_data(as_text=True))

        for i in range(24):
            self.assertIn('Reply {}'.format(i), resp.get_data(as_text=True))

        # Update the user profile and test again.
        # Should yield the same result as above but without expilict sort
        self.client.post(url_for('users.settings_profile'), data={
            'reply_sort_order': True,
        }, follow_redirects=True)

        resp = self.client.get(url_for('posts.view_post', username='user1',
                                       post_id=post1),
                               follow_redirects=True)

        for i in range(24):
            self.assertIn('Reply {}'.format(i), resp.get_data(as_text=True))

        # Ensure an incorrect sort renders the user default
        resp = self.client.get(url_for('posts.view_post', username='user1',
                                       post_id=post1, sort='cheese'),
                               follow_redirects=True)

        for i in range(24):
            self.assertIn('Reply {}'.format(i), resp.get_data(as_text=True))

    def test_replies(self):
        """
        Test commenting on a post. This is a lot simpler than making a post
        """
        # We can not test getting to a comment as we need a post and a user
        # for this too happen

        # Let's create a user and login
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        # Activate the account
        activate(user1)
        # Log the user in
        resp = self.client.post(url_for('auth.signin'), data={
            'username': 'user1',
            'password': 'Password'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        # Create a post to comment on we will do this in the backend to get
        # the pid
        post1 = create_post(user1, 'user1', 'Test post')

        # Lets attempt to GET to the comment view. Should fail we can only POST
        # like we can to /post
        resp = self.client.get(url_for('posts.post', username='user1',
                                       post_id=post1))
        # Method not allowed
        self.assertEqual(resp.status_code, 405)

        # Lets post a comment and follow the redirects this should take us to
        # the comment page
        resp = self.client.post(url_for('posts.post', username='user1',
                                        post_id=post1),
                                data={'body': 'Test comment'},
                                follow_redirects=True)
        # Lets check that we can see the comment
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Test comment', resp.get_data(as_text=True))
        # Lets also make sure the form is visible on the page
        self.assertIn('<!-- author reply -->', resp.get_data(as_text=True))

        # Lets signout
        resp = self.client.get(url_for('auth.signout'))
        self.assertEqual(resp.status_code, 302)

        # Lets create another test user and ensure that they can see the
        # comment
        user2 = create_account('user2', 'user2@pjuu.com', 'password')
        # Activate the account
        activate(user2)
        # Log the user in
        resp = self.client.post(url_for('auth.signin'), data={
            'username': 'user2',
            'password': 'password'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        # Lets just check that we can see the comment if we go to the view_post
        # view
        resp = self.client.get(url_for('posts.view_post', username='user1',
                                       post_id=post1))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Test comment', resp.get_data(as_text=True))

        # Lets comment ourselves
        resp = self.client.post(url_for('posts.post', username='user1',
                                        post_id=post1),
                                data={'body': 'Test comment 2'},
                                follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        # Check that the 2 comments exist
        self.assertIn('Test comment', resp.get_data(as_text=True))
        self.assertIn('Test comment 2', resp.get_data(as_text=True))

        # Lets check we can not comment if we are muted
        mute(user2)
        resp = self.client.post(url_for('posts.post', username='user1',
                                        post_id=post1),
                                data={'body': 'Muting test'},
                                follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        # Check that the comment was never posted
        self.assertIn('You have been silenced!', resp.get_data(as_text=True))
        self.assertNotIn('Muting test', resp.get_data(as_text=True))

        # Reverse the muting and test again
        mute(user2, False)
        resp = self.client.post(url_for('posts.post', username='user1',
                                        post_id=post1),
                                data={'body': 'Muting test'},
                                follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        # Check that the comment was never posted
        self.assertNotIn('You have been silenced!',
                         resp.get_data(as_text=True))
        self.assertIn('Muting test', resp.get_data(as_text=True))

        # Try and post to many characters
        resp = self.client.post(url_for('posts.post', username='user1',
                                        post_id=post1), data={
            'body': ('P' * (MAX_POST_LENGTH + 1))
        }, follow_redirects=True)
        self.assertIn('Posts can not be larger than '
                      '{0} characters'.format(MAX_POST_LENGTH),
                      resp.get_data(as_text=True))

        # Test replies with an image
        image = io.BytesIO(
            open('tests/upload_test_files/otter.jpg', 'rb').read())
        resp = self.client.post(
            url_for('posts.post', username='user1', post_id=post1),
            data={
                'body': 'Test upload',
                'upload': (image, 'otter.jpg')
            },
            follow_redirects=True
        )

        self.assertEqual(resp.status_code, 200)

        # So that we can check the data is in the templates, upload a post
        # in the backend and ensure it appears where it should
        image = io.BytesIO(
            open('tests/upload_test_files/otter.png', 'rb').read())
        reply_img = create_post(user1, 'user1', 'Test post', reply_to=post1,
                                upload=image)
        self.assertIsNotNone(reply_img)
        reply = get_post(reply_img)
        resp = self.client.get(url_for('posts.view_post', username='user1',
                                       post_id=post1))
        self.assertIn('<!-- upload:reply:{} -->'.format(reply_img),
                      resp.get_data(as_text=True))
        self.assertIn('<img src="{}"/>'.format(
            url_for('posts.get_upload', filename=reply.get('upload'))),
            resp.get_data(as_text=True))

        # Ensure that posting an image with no text allows it
        image = io.BytesIO(
            open('tests/upload_test_files/otter.jpg', 'rb').read())
        resp = self.client.post(
            url_for('posts.post', username='user1', post_id=post1),
            data={
                'body': '',
                'upload': (image, 'otter.jpg')
            },
            follow_redirects=True
        )
        self.assertEqual(resp.status_code, 200)

        # Ensure that an invalid filename is stopped by the forms
        image = io.BytesIO(
            open('tests/upload_test_files/otter.jpg', 'rb').read())
        resp = self.client.post(
            url_for('posts.post', username='user1', post_id=post1),
            data={
                'body': 'Test',
                'upload': (image, 'otter.cheese')
            },
            follow_redirects=True
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Only "gif", "jpg", "jpeg" and "png" files are '
                      'supported', resp.get_data(as_text=True))

        # Check a user can not reply to an invalid post
        resp = self.client.post(
            url_for('posts.post', username='user2', post_id=post1),
            data={
                'body': 'Test',
            },
            follow_redirects=True
        )
        self.assertEqual(resp.status_code, 404)
        # Done for now

    def test_up_down_vote(self):
        """
        Test voting up and down on both comments and posts
        """
        # Create three users to test this. This is what we need to check this.
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        user2 = create_account('user2', 'user2@pjuu.com', 'Password')
        user3 = create_account('user3', 'user3@pjuu.com', 'Password')
        # Activate the accounts
        activate(user1)
        activate(user2)
        activate(user3)

        # Create a post as the first user
        post1 = create_post(user1, 'user1', 'Post user 1')
        # Create a post as user 2
        post2 = create_post(user2, 'user2', 'Post user 2')
        # Create comment as user two on user 1's comment
        comment1 = create_post(user2, 'user2', 'Comment user 2', post1)

        # Create a second post for user 2 we will use this to ensure we can't
        # vote on out own post
        post3 = create_post(user1, 'user1', 'Second post user 1')
        # We will have 1 comment from user 1 on this post by user 1 to ensure
        # that we can't vote on either
        comment2 = create_post(user1, 'user1', 'Comment user 1', post3)

        # We will now actually test the frontend
        # Log in as user 1
        resp = self.client.post(url_for('auth.signin'), data={
            'username': 'user1',
            'password': 'Password'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        # Lets ensure both vote links are there
        resp = self.client.get(url_for('posts.view_post', username='user2',
                                       post_id=post2))
        self.assertIn('<!-- upvote:post:{} -->'.format(post2),
                      resp.get_data(as_text=True))
        self.assertIn('<!-- downvote:post:{} -->'.format(post2),
                      resp.get_data(as_text=True))
        self.assertNotIn('<!-- upvoted:post:{} -->'.format(post2),
                         resp.get_data(as_text=True))
        self.assertNotIn('<!-- downvoted:post:{} -->'.format(post2),
                         resp.get_data(as_text=True))

        # Visit user 2's comment and UPVOTE that
        resp = self.client.post(url_for('posts.upvote', username='user2',
                                        post_id=post2),
                                follow_redirects=True)
        # We should now be at the posts page
        self.assertEqual(resp.status_code, 200)
        self.assertIn('You upvoted the post', resp.get_data(as_text=True))
        # You can reverse votes so the downvote button should still
        # be present on the page.
        # So shoudl the upvote button button it should be marked as
        # Upvoted.
        self.assertIn('<!-- upvoted:post:{} -->'.format(post2),
                      resp.get_data(as_text=True))
        self.assertNotIn('<!-- upvote:post:{} -->'.format(post2),
                         resp.get_data(as_text=True))
        self.assertIn('<!-- downvote:post:{} -->'.format(post2),
                      resp.get_data(as_text=True))
        self.assertNotIn('<!-- downvoted:post:{} -->'.format(post2),
                         resp.get_data(as_text=True))

        # Let's try and vote on that post again
        resp = self.client.post(url_for('posts.upvote', username='user2',
                                        post_id=post2),
                                follow_redirects=True)
        # We should now be at the posts page
        self.assertEqual(resp.status_code, 200)
        # The vote shoudl have been reversed and we should be informed
        self.assertIn('You reversed your vote on the post',
                      resp.get_data(as_text=True))

        # Visit our own post and ensure that user 2s comment is there
        # There will be only one set of arrows as we can't vote on our own post
        # we will check that part later on
        resp = self.client.get(url_for('posts.view_post', username='user1',
                                       post_id=post1))
        self.assertIn('Comment user 2', resp.get_data(as_text=True))
        self.assertIn('<!-- upvote:reply:{0} -->'.format(comment1),
                      resp.get_data(as_text=True))
        self.assertIn('<!-- downvote:reply:{0} -->'.format(comment1),
                      resp.get_data(as_text=True))

        # Down vote the users comment (it's nothing personal test2 :P)
        resp = self.client.post(url_for('posts.downvote', username='user1',
                                        post_id=post1, reply_id=comment1),
                                follow_redirects=True)
        self.assertIn('You downvoted the comment', resp.get_data(as_text=True))
        self.assertIn('<!-- downvoted:reply:{0} -->'.format(comment1),
                      resp.get_data(as_text=True))
        self.assertNotIn('<!-- downvote:reply:{0} -->'.format(comment1),
                         resp.get_data(as_text=True))
        self.assertIn('<!-- upvote:reply:{0} -->'.format(comment1),
                      resp.get_data(as_text=True))
        self.assertNotIn('<!-- downvote:reply:{0} -->'.format(comment1),
                         resp.get_data(as_text=True))

        # Lets check that we can't vote on this comment again
        resp = self.client.post(url_for('posts.downvote', username='user1',
                                        post_id=post1, reply_id=comment1),
                                follow_redirects=True)
        self.assertIn('You reversed your vote on the comment',
                      resp.get_data(as_text=True))

        # Now lets double check we can't vote on our own comments or posts
        # We will visit post 3 first and ensure there is no buttons being shown
        resp = self.client.get(url_for('posts.view_post', username='user1',
                                       post_id=post3))
        self.assertNotIn('<!-- action:upvote -->', resp.get_data(as_text=True))
        self.assertNotIn('<!-- action:downvote -->',
                         resp.get_data(as_text=True))
        # Check that the comment is there
        self.assertIn('Comment user 1', resp.get_data(as_text=True))

        # Lets ensure we can't vote on either the comment or the post
        resp = self.client.post(url_for('posts.upvote', username='user1',
                                        post_id=post3),
                                follow_redirects=True)
        self.assertIn('You can not vote on your own posts',
                      resp.get_data(as_text=True))

        resp = self.client.post(url_for('posts.upvote', username='user1',
                                        post_id=post3, reply_id=comment2),
                                follow_redirects=True)
        self.assertIn('You can not vote on your own posts',
                      resp.get_data(as_text=True))

        # Try and vote on a comment or post that does not exist
        # Vote on a post
        resp = self.client.post(url_for('posts.upvote', username='user1',
                                        post_id=k.NIL_VALUE),
                                follow_redirects=True)
        self.assertEqual(resp.status_code, 404)
        # Vote on a comment
        resp = self.client.post(url_for('posts.downvote', username='user1',
                                        post_id=post3, reply_id=k.NIL_VALUE),
                                follow_redirects=True)
        self.assertEqual(resp.status_code, 404)
        # Vote on a post when the user doesn't even exists
        resp = self.client.post(url_for('posts.downvote', username='userX',
                                        post_id=post3, reply_id=k.NIL_VALUE),
                                follow_redirects=True)
        self.assertEqual(resp.status_code, 404)

        # Let's ensure a logged out user can not perform any of these actions
        # Signout
        self.client.get(url_for('auth.signout'), follow_redirects=True)
        # We are at the signin page
        # Vote on a post
        resp = self.client.post(url_for('posts.upvote', username='user1',
                                        post_id=post3),
                                follow_redirects=True)
        self.assertIn('You need to be signed in to view that',
                      resp.get_data(as_text=True))
        # Vote on a comment
        resp = self.client.post(url_for('posts.downvote', username='user1',
                                        post_id=post3, reply_id=comment2),
                                follow_redirects=True)
        self.assertIn('You need to be signed in to view that',
                      resp.get_data(as_text=True))

        # Log in as user3 and try and catch some situations which are missing
        # from coverage.
        resp = self.client.post(url_for('auth.signin'), data={
            'username': 'user3',
            'password': 'Password'
        }, follow_redirects=True)
        # Downvote user1's post
        resp = self.client.post(url_for('posts.downvote', username='user1',
                                        post_id=post1),
                                follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        # Create a post and try and downvote it
        post4 = create_post(user3, 'user3', 'Test post')
        resp = self.client.post(url_for('posts.downvote', username='user3',
                                        post_id=post4),
                                follow_redirects=True)
        self.assertIn('You can not vote on your own posts',
                      resp.get_data(as_text=True))

        # Log back in as user1 and vote on the previous posts we
        # reversed. Becasue we reversed them there is no vote logged so
        # no time out.
        self.client.get(url_for('auth.signout'), follow_redirects=True)
        resp = self.client.post(url_for('auth.signin'), data={
            'username': 'user1',
            'password': 'Password'
        }, follow_redirects=True)

        resp = self.client.post(url_for('posts.upvote', username='user2',
                                        post_id=post2),
                                follow_redirects=True)
        self.assertIn('You upvoted the post', resp.get_data(as_text=True))

        resp = self.client.post(url_for('posts.upvote', username='user1',
                                        post_id=post1, reply_id=comment1),
                                follow_redirects=True)
        self.assertIn('You upvoted the comment', resp.get_data(as_text=True))

        # With the new time based vote reversal/revote it is VERY hard
        # to test from the front end that you have already voted because
        # they run to quickly.
        # We are going to have to change the k.VOTE_TIMEOUT value to a
        # more managable number and sleep. (1 sec)
        # Please DO NOT follow my lead. This is duck punching/monkey
        # patching to the point of stupidity.
        pjuu.lib.keys.VOTE_TIMEOUT = 1
        sleep(1)

        resp = self.client.post(url_for('posts.upvote', username='user2',
                                        post_id=post2),
                                follow_redirects=True)
        self.assertIn('You have already voted on this post',
                      resp.get_data(as_text=True))

        resp = self.client.post(url_for('posts.downvote', username='user1',
                                        post_id=post1, reply_id=comment1),
                                follow_redirects=True)
        self.assertIn('You have already voted on this post',
                      resp.get_data(as_text=True))

        # Reset the value just in case we change it
        pjuu.lib.keys.VOTE_TIMEOUT = k.VOTE_TIMEOUT

    def test_up_down_vote_xhr(self):
        """Ensure we get the correct responses if we vote via XHR"""
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        user2 = create_account('user2', 'user2@pjuu.com', 'Password')

        activate(user1)
        activate(user2)

        post1 = create_post(user1, 'user1', 'Post user 1')
        post2 = create_post(user2, 'user2', 'Post user 2')

        resp = self.client.post(url_for('auth.signin'), data={
            'username': 'user2',
            'password': 'Password'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        # Ensure we can up vote via XHR
        resp = self.client.post(
            url_for('posts.upvote', username='user1', post_id=post1),
            headers=[('X-Requested-With', 'XMLHttpRequest')]
        )
        resp_json = json.loads(resp.get_data(as_text=True))
        self.assertEqual(resp_json.get('message'), 'You upvoted the post')

        # Ensure we can reverse a vote
        resp = self.client.post(
            url_for('posts.upvote', username='user1', post_id=post1),
            headers=[('X-Requested-With', 'XMLHttpRequest')]
        )
        resp_json = json.loads(resp.get_data(as_text=True))
        self.assertEqual(resp_json.get('message'),
                         'You reversed your vote on the post')

        # Ensure we can downvote the post
        resp = self.client.post(
            url_for('posts.downvote', username='user1', post_id=post1),
            headers=[('X-Requested-With', 'XMLHttpRequest')]
        )
        resp_json = json.loads(resp.get_data(as_text=True))
        self.assertEqual(resp_json.get('message'), 'You downvoted the post')

        resp = self.client.post(
            url_for('posts.downvote', username='user1', post_id=post1),
            headers=[('X-Requested-With', 'XMLHttpRequest')]
        )
        resp_json = json.loads(resp.get_data(as_text=True))
        self.assertEqual(resp_json.get('message'),
                         'You reversed your vote on the post')

        # Test failure conditions
        # Missing vote (invalid ID's)
        resp = self.client.post(
            url_for('posts.downvote', username='user1', post_id='cheese'),
            headers=[('X-Requested-With', 'XMLHttpRequest')]
        )
        resp_json = json.loads(resp.get_data(as_text=True))
        self.assertEqual(resp_json.get('message'), 'Post not found')

        # Vote on own
        resp = self.client.post(
            url_for('posts.downvote', username='user2', post_id=post2),
            headers=[('X-Requested-With', 'XMLHttpRequest')]
        )
        resp_json = json.loads(resp.get_data(as_text=True))
        self.assertEqual(resp_json.get('message'),
                         'You can not vote on your own posts')

        # Upvote so there is a vote
        resp = self.client.post(
            url_for('posts.upvote', username='user1', post_id=post1),
            headers=[('X-Requested-With', 'XMLHttpRequest')]
        )

        # Vote time out. See above test case for more details
        pjuu.lib.keys.VOTE_TIMEOUT = 1
        sleep(1)

        resp = self.client.post(
            url_for('posts.upvote', username='user1', post_id=post1),
            headers=[('X-Requested-With', 'XMLHttpRequest')]
        )
        resp_json = json.loads(resp.get_data(as_text=True))
        self.assertEqual(resp_json.get('message'),
                         'You have already voted on this post')

        resp = self.client.post(
            url_for('posts.downvote', username='user1', post_id=post1),
            headers=[('X-Requested-With', 'XMLHttpRequest')]
        )
        resp_json = json.loads(resp.get_data(as_text=True))
        self.assertEqual(resp_json.get('message'),
                         'You have already voted on this post')

        # Reset the value just in case we change it
        pjuu.lib.keys.VOTE_TIMEOUT = k.VOTE_TIMEOUT

    def test_flagging(self):
        """Ensure flagging works as expected"""
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        user2 = create_account('user2', 'user2@pjuu.com', 'Password')

        activate(user1)
        activate(user2)

        # Ensure both users are following each other
        follow_user(user1, user2)
        follow_user(user2, user1)

        post1 = create_post(user1, 'user1', 'Post user 1')
        post2 = create_post(user2, 'user2', 'Post user 2')
        comment1 = create_post(user2, 'user2', 'Comment user 2', post1)
        comment2 = create_post(user1, 'user1', 'Comment user 1', post1)

        # Ensure user 1 only sees the flag for post that aren't his
        resp = self.client.post(url_for('auth.signin'), data={
            'username': 'user1',
            'password': 'Password'
        }, follow_redirects=True)
        self.assertIn('<h1>Feed</h1>', resp.get_data(as_text=True))

        self.assertIn('<!-- list:post:{0} -->'.format(post1),
                      resp.get_data(as_text=True))
        self.assertIn('<!-- list:post:{0} -->'.format(post2),
                      resp.get_data(as_text=True))

        # You can not flag a top level post without visiting it.
        self.assertNotIn('<!-- flag:post:{0} -->'.format(post1),
                         resp.get_data(as_text=True))
        self.assertNotIn('<!-- flag:post:{0} -->'.format(post2),
                         resp.get_data(as_text=True))

        # Ensure user1 can't see a flag on his post or comments but can on
        # user2s reply
        resp = self.client.get(url_for('posts.view_post', username='user1',
                                       post_id=post1))
        self.assertNotIn('<!-- flag:post:{0} -->'.format(post1),
                         resp.get_data(as_text=True))
        self.assertNotIn('<!-- flag:post:{0} -->'.format(comment2),
                         resp.get_data(as_text=True))
        self.assertIn('<!-- flag:post:{0} -->'.format(comment1),
                      resp.get_data(as_text=True))

        # Ensure a user can not flag his own post or comment
        resp = self.client.post(url_for('posts.flag', username='user1',
                                        post_id=post1),
                                follow_redirects=True)
        self.assertIn('You can not flag on your own posts',
                      resp.get_data(as_text=True))

        resp = self.client.post(url_for('posts.flag', username='user1',
                                        post_id=post1, reply_id=comment2),
                                follow_redirects=True)
        self.assertIn('You can not flag on your own posts',
                      resp.get_data(as_text=True))

        # Post should not be flagged
        self.assertFalse(has_flagged(user1, post2))
        self.assertIsNone(get_post(post2).get('flags'))

        # Ensure user1 can flag user2s post
        resp = self.client.post(url_for('posts.flag', username='user2',
                                        post_id=post2),
                                follow_redirects=True)
        self.assertIn('You flagged the post', resp.get_data(as_text=True))

        # Are they listed as flagged
        self.assertTrue(has_flagged(user1, post2))
        self.assertEqual(get_post(post2).get('flags'), 1)

        # Ensure user1 can un-flag user2s post
        resp = self.client.post(url_for('posts.flag', username='user2',
                                        post_id=post2),
                                follow_redirects=True)
        self.assertIn('You have already flagged this post',
                      resp.get_data(as_text=True))

        # Are they listed as flagged
        self.assertTrue(has_flagged(user1, post2))
        self.assertEqual(get_post(post2).get('flags'), 1)

        # Comment should not be flagged
        self.assertFalse(has_flagged(user1, comment1))
        self.assertIsNone(get_post(comment1).get('flags'))

        # Ensure user1 can flag user2s comment
        resp = self.client.post(url_for('posts.flag', username='user2',
                                        post_id=comment1),
                                follow_redirects=True)
        self.assertIn('You flagged the comment', resp.get_data(as_text=True))

        # Are they listed as flagged
        self.assertTrue(has_flagged(user1, comment1))
        self.assertEqual(get_post(comment1).get('flags'), 1)

        # Ensure user2 can't flag a post again'
        resp = self.client.post(url_for('posts.flag', username='user2',
                                        post_id=comment1),
                                follow_redirects=True)
        self.assertIn('You have already flagged this post',
                      resp.get_data(as_text=True))

        # Are they listed as flagged
        self.assertTrue(has_flagged(user1, comment1))
        self.assertEqual(get_post(comment1).get('flags'), 1)

        # Ensure we can not flag a non existant post
        resp = self.client.post(url_for('posts.flag', username='user3',
                                        post_id=comment1),
                                follow_redirects=True)
        self.assertEqual(resp.status_code, 404)

    def test_unflagging(self):
        """Ensure OP users can un-flag a post."""
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        user2 = create_account('user2', 'user2@pjuu.com', 'Password')

        activate(user1)
        activate(user2)

        bite(user1)

        post1 = create_post(user2, 'user2', 'Test post user 2')

        flag_post(user1, post1)

        # Ensure the post has a flag
        self.assertEqual(m.db.posts.find_one({'_id': post1}).get('flags'), 1)

        # Ensure a non-OP user can not unflag posts
        resp = self.client.post(url_for('auth.signin'), data={
            'username': 'user2',
            'password': 'Password'
        }, follow_redirects=True)
        resp = self.client.get(url_for('posts.unflag_post', post_id=post1))

        self.assertEqual(resp.status_code, 403)

        self.client.get(url_for('auth.signout'))

        # Ensure user1 (op) can unflag a post
        resp = self.client.post(url_for('auth.signin'), data={
            'username': 'user1',
            'password': 'Password'
        }, follow_redirects=True)

        resp = self.client.get(url_for('posts.unflag_post', post_id=post1),
                               follow_redirects=True)
        self.assertIn('Flags have been reset for post',
                      resp.get_data(as_text=True))

        self.assertEqual(m.db.posts.find_one({'_id': post1}).get('flags'), 0)

        # Ensure we can not unflag a non-existant post
        resp = self.client.get(url_for('posts.unflag_post', post_id='NA'),
                               follow_redirects=True)
        self.assertEqual(resp.status_code, 404)

    def test_delete_post_comment(self):
        """
        Let's test the ability to delete posts and comments
        """
        # Create 3 users for this
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        user2 = create_account('user2', 'user2@pjuu.com', 'Password')
        user3 = create_account('user3', 'user3@pjuu.com', 'Password')
        # Activate the accounts
        activate(user1)
        activate(user2)
        activate(user3)
        # Create a test post as each user
        post1 = create_post(user1, 'user1', 'Test post, user 1')
        post2 = create_post(user2, 'user2', 'Test post, user 2')
        create_post(user3, 'user3', 'Test post, user 3')

        # Log in as user 1
        resp = self.client.post(url_for('auth.signin'), data={
            'username': 'user1',
            'password': 'Password'
        }, follow_redirects=True)
        self.assertIn('<h1>Feed</h1>', resp.get_data(as_text=True))

        # Visit our own post and ensure the delete button is there
        resp = self.client.get(url_for('posts.view_post', username='user1',
                                       post_id=post1))
        self.assertIn('<!-- delete:post:{0} -->'.format(post1),
                      resp.get_data(as_text=True))
        # Visit test2's post and ensure button is not there
        resp = self.client.get(url_for('posts.view_post', username='user2',
                                       post_id=post2))
        self.assertNotIn('<!-- delete:post:{0} -->'.format(post2),
                         resp.get_data(as_text=True))

        # Try and delete user two's post this should fail
        resp = self.client.post(url_for('posts.delete_post', username='user2',
                                        post_id=post2))
        self.assertEqual(resp.status_code, 403)
        # Ensure the post is still actuall there
        resp = self.client.get(url_for('posts.view_post', username='user2',
                                       post_id=post2))
        self.assertIn('Test post, user 2', resp.get_data(as_text=True))

        # Try and delete a non-existant post
        resp = self.client.post(url_for('posts.delete_post',
                                        username=k.NIL_VALUE,
                                        post_id=k.NIL_VALUE))
        self.assertEqual(resp.status_code, 404)

        # Let's delete our own post
        resp = self.client.post(url_for('posts.delete_post', username='user1',
                                        post_id=post1),
                                follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Post has been deleted along with all replies',
                      resp.get_data(as_text=True))
        # Let's ensure the post no longer exists
        resp = self.client.get(url_for('posts.view_post', username='user1',
                                       post_id=post1))
        self.assertEqual(resp.status_code, 404)

        # Create a comment for each user on the only remaining post (2)
        comment1 = create_post(user1, 'user1', 'Test comment, user 1', post2)
        comment2 = create_post(user2, 'user2', 'Test comment, user 2', post2)
        comment3 = create_post(user3, 'user3', 'Test comment, user 3', post2)

        # Visit the post ensure the comments are there and there is a delete
        # button, there should only be one as we are user 1 :)
        resp = self.client.get(url_for('posts.view_post', username='user2',
                                       post_id=post2))
        # Make sure both comments are there
        self.assertIn('Test comment, user 1', resp.get_data(as_text=True))
        self.assertIn('Test comment, user 2', resp.get_data(as_text=True))
        self.assertIn('Test comment, user 3', resp.get_data(as_text=True))

        # Check that the URL's are correct for deleting these comments
        # This was an issue previously, see Github issue #24
        # We can only check this for user1's comment as its ours
        self.assertIn(
            url_for('posts.delete_post', username='user2',
                    post_id=post2, reply_id=comment1),
            resp.get_data(as_text=True))

        # Let's delete are own comment
        resp = self.client.post(url_for('posts.delete_post', username='user2',
                                        post_id=post2, reply_id=comment1),
                                follow_redirects=True)
        # Check we have confirmation
        self.assertIn('Post has been deleted', resp.get_data(as_text=True))
        # Lets check that comment 2 is there
        self.assertIn('Test comment, user 2', resp.get_data(as_text=True))
        self.assertIn('Test comment, user 3', resp.get_data(as_text=True))
        # Lets ensure our comment is gone
        self.assertNotIn('Test comment, user 1', resp.get_data(as_text=True))

        # Attempt to delete user 2's comment. This should fail with a 403
        # as we are neither the comment author nor the post author
        resp = self.client.post(url_for('posts.delete_post', username='user2',
                                        post_id=post2, reply_id=comment2),
                                follow_redirects=True)
        # Let's check we got the error
        self.assertEqual(resp.status_code, 403)

        # Attempt to delete user 2's post we should receive a 403
        resp = self.client.post(url_for('posts.delete_post', username='user2',
                                        post_id=post2, reply_id=comment2))
        self.assertEqual(resp.status_code, 403)

        # Let's just ensure the comment wasn't deleted
        resp = self.client.get(url_for('posts.view_post', username='user2',
                                       post_id=post2))
        self.assertIn('Test comment, user 2', resp.get_data(as_text=True))

        # Try and delete a non-existant comment
        resp = self.client.post(url_for('posts.delete_post',
                                        username=k.NIL_VALUE,
                                        post_id=k.NIL_VALUE,
                                        reply_id=k.NIL_VALUE))
        self.assertEqual(resp.status_code, 404)

        # Log out as user 1
        self.client.get(url_for('auth.signout'))

        # Log in as user test2 and delete user test3's comment
        # Test2 is the post author so they should be able to delete not their
        # own comments

        resp = self.client.post(url_for('auth.signin'), data={
            'username': 'user2',
            'password': 'Password'
        }, follow_redirects=True)
        self.assertIn('<h1>Feed</h1>', resp.get_data(as_text=True))

        # Goto test2s post
        resp = self.client.get(url_for('posts.view_post', username='user2',
                                       post_id=post2))
        # Ensure test2 and test3s comments are there but not test1
        self.assertIn('Test comment, user 2', resp.get_data(as_text=True))
        self.assertIn('Test comment, user 3', resp.get_data(as_text=True))
        self.assertNotIn('Test comment, user 1', resp.get_data(as_text=True))

        # No need to test that test2 can delete there own post as we have
        # tested this already with test1.
        # Check that the owner of the post (user2) can delete any comment
        resp = self.client.post(url_for('posts.delete_post', username='user2',
                                        post_id=post2, reply_id=comment3),
                                follow_redirects=True)
        # Check we have confirmation
        self.assertIn('Post has been deleted', resp.get_data(as_text=True))
        # Lets check that comment 2 is there
        self.assertIn('Test comment, user 2', resp.get_data(as_text=True))
        # Lets ensure our comment is gone
        self.assertNotIn('Test comment, user 1', resp.get_data(as_text=True))
        self.assertNotIn('Test comment, user 3', resp.get_data(as_text=True))

        # Done for now

    def test_subscriptions(self):
        """
        Test that subscriptions work through the frontend.

        This mainly just tests unsubscribe button as the rest is tested in the
        backend.
        """
        # Create 3 users for this
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        user2 = create_account('user2', 'user2@pjuu.com', 'Password')
        user3 = create_account('user3', 'user3@pjuu.com', 'Password')
        # Activate the accounts
        activate(user1)
        activate(user2)
        activate(user3)

        # Create a test post as user1 and tag user2 in it this way be can
        # see if they are also subscribed. Tag someone twice (user2) and
        # someone who doesn't exist
        post1 = create_post(user1, 'user1',
                            'Test post, hello @user2 @user2 @test4')

        # Login as test1
        # Don't bother testing this AGAIN
        self.client.post(url_for('auth.signin'), data={
            'username': 'user1',
            'password': 'Password'
        })

        # Visit the posts page and ensure unsubscribe button is there
        # We should have been subscribed when create_post was run above
        resp = self.client.get(url_for('posts.view_post', username='user1',
                                       post_id=post1))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('<!-- unsubscribe:post:{0} -->'.format(post1),
                      resp.get_data(as_text=True))

        # Unsubscribe via the frontend and ensure the button is removed and
        # we get a flash message
        resp = self.client.post(url_for('posts.unsubscribe', username='user1',
                                        post_id=post1),
                                follow_redirects=True)
        self.assertIn('You have been unsubscribed from this post',
                      resp.get_data(as_text=True))
        self.assertNotIn('<!-- unsubscribe:post:{0} -->'.format(post1),
                         resp.get_data(as_text=True))

        # Logout as user1
        self.client.get(url_for('auth.signout'))

        # Log in as user2 an ensure that they can see the subscription button
        self.client.post(url_for('auth.signin'), data={
            'username': 'user2',
            'password': 'Password'
        })
        resp = self.client.get(url_for('posts.view_post', username='user1',
                                       post_id=post1))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('<!-- unsubscribe:post:{0} -->'.format(post1),
                      resp.get_data(as_text=True))

        # Check that unsubscribing from a non-existant (wont pass check post)
        # post will raise a 404
        resp = self.client.post(url_for('posts.unsubscribe',
                                        username=k.NIL_VALUE,
                                        post_id=k.NIL_VALUE))
        self.assertEqual(resp.status_code, 404)

        # Log out aster user2
        self.client.get(url_for('auth.signout'))

        # Log in as user3
        self.client.post(url_for('auth.signin'), data={
            'username': 'user3',
            'password': 'Password'
        })
        # Create a comment in the backend as user3 so that we can check if they
        # become subscribed to the post
        create_post(user3, 'user3', "Test comment", post1)
        # Do the same check as before
        resp = self.client.get(url_for('posts.view_post', username='user1',
                                       post_id=post1))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('<!-- unsubscribe:post:{0} -->'.format(post1),
                      resp.get_data(as_text=True))

        # Create a post as user1 which we will not be subscribed too and ensure
        # that no message is shown
        post2 = create_post(user1, 'user1', "Test post, for cant unsubscribe")
        resp = self.client.post(url_for('posts.unsubscribe', username='user1',
                                        post_id=post2),
                                follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn('You have been unsubscribed from this post',
                         resp.get_data(as_text=True))
        # Ensure we have gone to that post
        self.assertIn("Test post, for cant unsubscribe",
                      resp.get_data(as_text=True))

    def test_template_filters(self):
        """
        Small tests for the template filters. There is only a couple which
        are not tested by the rest of the unit tests.

        We will just test these by calling them directly not through the site.
        """
        # Test timeify with an invalid value (can't be converted to int)
        time_str = timeify_filter("None")
        self.assertEqual(time_str, 'Err')
        # Test timeify with an invaid type
        time_str = timeify_filter(None)
        self.assertEqual(time_str, 'Err')
        # Test that it works correctly
        # With an int
        time_str = timeify_filter(1412271814)
        self.assertNotEqual(time_str, 'Err')
        # With a string
        time_str = timeify_filter('1412271814')
        self.assertNotEqual(time_str, 'Err')

        # Test millify
        # Check incorrect type
        num_str = millify_filter(None)
        self.assertEqual(num_str, 'Err')
        # Check value's that can't be turned in to ints
        # Str
        num_str = millify_filter("None")
        self.assertEqual(num_str, 'Err')
        # Check it does actually work
        # Positive
        num_str = millify_filter(1000)
        self.assertEqual(num_str, "1K")
        # Negative
        num_str = millify_filter(-1000)
        self.assertEqual(num_str, "-1K")

        num_str = millify_filter(12500000)
        self.assertEqual(num_str, "12.5M")

        num_str = millify_filter(-1200)
        self.assertEqual(num_str, "-1.2K")

        num_str = millify_filter(3800)
        self.assertEqual(num_str, "3.8K")

    def test_postify(self):
        """Test that postify renders posts correctly when the correct
        informations is attached.

        .. note: This is not intended to test the parsing but simply that what
                 is parsed is rendered correctly.
        """
        # We need a user to post as.
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        activate(user1)

        self.client.post(url_for('auth.signin'), data={
            'username': 'user1',
            'password': 'Password'
        })

        # Create a post with a user that does not exist there should be no
        # rendering involved
        resp = self.client.post(url_for('posts.post'), data={
            'body': 'Hello @joe'
        }, follow_redirects=True)

        self.assertIn('Hello @joe', resp.get_data(as_text=True))

        # Create another user and then tag them
        user2 = create_account('user2', 'user2@pjuu.com', 'Password')
        activate(user2)

        resp = self.client.post(url_for('posts.post'), data={
            'body': 'Hello @user2'
        }, follow_redirects=True)

        self.assertIn('Hello <a href="{0}">@user2</a>'.format(
            url_for('users.profile', username='user2')),
            resp.get_data(as_text=True))

        # Check a link
        resp = self.client.post(url_for('posts.post'), data={
            'body': 'Visit https://pjuu.com'
        }, follow_redirects=True)

        self.assertIn('Visit <a href="https://pjuu.com" target="_blank">'
                      'https://pjuu.com</a>', resp.get_data(as_text=True))

        # Test a hashtag
        resp = self.client.post(url_for('posts.post'), data={
            'body': 'Wow #hashtag'
        }, follow_redirects=True)

        self.assertIn('Wow <a href="{0}">#hashtag</a>'.format(
            url_for('posts.hashtags', hashtag='hashtag')),
            resp.get_data(as_text=True))

    def test_hashtags(self):
        """Ensure the hashtags endpoint gives acts and gives the posts we
        expect.

        .. note: For parsing of these please see `test_posts_backend.py`.

        """
        # Ensure you can't get to the end point when no logged in.
        resp = self.client.get(url_for('posts.hashtags', hashtag='test'),
                               follow_redirects=True)
        self.assertIn('You need to be signed in to view that',
                      resp.get_data(as_text=True))

        # Sign in
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        activate(user1)
        self.client.post(url_for('auth.signin'), data={
            'username': 'user1',
            'password': 'Password'
        }, follow_redirects=True)

        # Check all conditions which will result in a 404
        resp = self.client.get(url_for('posts.hashtags'))
        self.assertEqual(404, resp.status_code)

        resp = self.client.get(url_for('posts.hashtags', hashtag=''))
        self.assertEqual(404, resp.status_code)

        resp = self.client.get(url_for('posts.hashtags', hashtag='a'))
        self.assertEqual(404, resp.status_code)

        # Check what is there at the moment which it will just echo our valid
        # hashtag back at us
        resp = self.client.get(url_for('posts.hashtags', hashtag='pjuu'))
        self.assertEqual(200, resp.status_code)
        self.assertIn('<h1>Hashtag: pjuu</h1>', resp.get_data(as_text=True))
        self.assertIn('Empty', resp.get_data(as_text=True))

        # Create a post with a hash tag to ensure we can get it
        resp = self.client.post(
            url_for('posts.post', next=url_for('posts.hashtags',
                                               hashtag='ace')), data={
                'body': 'This is a new hashtag #ace'
            }, follow_redirects=True)
        self.assertIn('<h1>Hashtag: ace</h1>', resp.get_data(as_text=True))
        self.assertIn('This is a new hashtag <a href="{0}">#ace</a>'.format(
            url_for('posts.hashtags', hashtag='ace')),
            resp.get_data(as_text=True))

    def test_permissions_post_actions(self):
        """Ensure permission prevent actions"""
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        user2 = create_account('user2', 'user2@pjuu.com', 'Password')
        activate(user1)
        activate(user2)

        post1 = create_post(user1, 'user1', 'Approved post',
                            permission=k.PERM_APPROVED)
        self.client.post(url_for('auth.signin'), data={
            'username': 'user2',
            'password': 'Password'
        }, follow_redirects=True)

        resp = self.client.get(url_for('posts.view_post', username='user1',
                               post_id=post1))
        self.assertEqual(resp.status_code, 403)

        resp = self.client.post(url_for('posts.upvote', username='user1',
                                        post_id=post1, next='/'),
                                follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('You do not have permission to vote on this post',
                      resp.get_data(as_text=True))

        resp = self.client.post(url_for('posts.downvote', username='user1',
                                        post_id=post1, next='/'),
                                follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('You do not have permission to vote on this post',
                      resp.get_data(as_text=True))

        # Test voting with XHR
        resp = self.client.post(
            url_for('posts.upvote', username='user1', post_id=post1),
            headers=[('X-Requested-With', 'XMLHttpRequest')]
        )
        resp_json = json.loads(resp.get_data(as_text=True))
        self.assertEqual(resp_json.get('message'),
                         'You do not have permission to vote on this post')

        resp = self.client.post(
            url_for('posts.downvote', username='user1', post_id=post1),
            headers=[('X-Requested-With', 'XMLHttpRequest')]
        )
        resp_json = json.loads(resp.get_data(as_text=True))
        self.assertEqual(resp_json.get('message'),
                         'You do not have permission to vote on this post')

        resp = self.client.post(url_for('posts.flag', username='user1',
                                        post_id=post1, next='/'),
                                follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('You do not have permission to flag this post',
                      resp.get_data(as_text=True))

        # Ensure user 2 can't comment on post1
        resp = self.client.post(url_for('posts.post', username='user1',
                                post_id=post1), data={
            'body': 'Test'
        })
        self.assertEqual(resp.status_code, 403)

        # Have user2 follow user1 and have user1 approve user2
        follow_user(user2, user1)
        approve_user(user1, user2)

        resp = self.client.post(url_for('posts.post', username='user1',
                                post_id=post1), data={
            'body': 'Test'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Test', resp.get_data(as_text=True))

        # Signout as user2 and ensure user1 can comment on the post.
        self.client.get(url_for('auth.signout'))
        self.client.post(url_for('auth.signin'), data={
            'username': 'user1',
            'password': 'Password'
        }, follow_redirects=True)

        resp = self.client.post(url_for('posts.post', username='user1',
                                post_id=post1), data={
            'body': 'Cheese'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Test', resp.get_data(as_text=True))
        self.assertIn('Cheese', resp.get_data(as_text=True))

    def test_posting_with_permissions(self):
        """Ensure only the correct permissions can be applied to a post"""
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        activate(user1)

        self.client.post(url_for('auth.signin'), data={
            'username': 'user1',
            'password': 'Password'
        }, follow_redirects=True)

        resp = self.client.post(url_for('posts.post'), data={
            'body': 'Test post',
            'permission': 4
        }, follow_redirects=True)
        self.assertIn('Not a valid choice', resp.get_data(as_text=True))

        resp = self.client.post(url_for('posts.post'), data={
            'body': 'Test post',
            'permission': 'cheese'
        }, follow_redirects=True)
        self.assertIn('Not a valid choice', resp.get_data(as_text=True))

    def test_global_feeds(self):
        """"""
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        user2 = create_account('user2', 'user2@pjuu.com', 'Password')
        activate(user1)
        activate(user2)

        for i in [('public', 0), ('pjuu', 1), ('trusted', 2)]:
            for j in range(1, 4):
                create_post(user1, 'user1', '{} post #{}'.format(i[0], j),
                            permission=i[1])

        # Test a non-logged in use
        resp = self.client.get(url_for('posts.global_feed'))
        self.assertIn('public post #1', resp.get_data(as_text=True))
        self.assertIn('public post #2', resp.get_data(as_text=True))
        self.assertIn('public post #3', resp.get_data(as_text=True))

        self.assertNotIn('pjuu post #1', resp.get_data(as_text=True))
        self.assertNotIn('pjuu post #2', resp.get_data(as_text=True))
        self.assertNotIn('pjuu post #3', resp.get_data(as_text=True))

        self.assertNotIn('trusted post #1', resp.get_data(as_text=True))
        self.assertNotIn('trusted post #2', resp.get_data(as_text=True))
        self.assertNotIn('trusted post #3', resp.get_data(as_text=True))

        # Test logged in user
        self.client.post(url_for('auth.signin'), data={
            'username': 'user2',
            'password': 'Password'
        }, follow_redirects=True)

        resp = self.client.get(url_for('posts.global_feed'))
        self.assertIn('public post #1', resp.get_data(as_text=True))
        self.assertIn('public post #2', resp.get_data(as_text=True))
        self.assertIn('public post #3', resp.get_data(as_text=True))

        self.assertIn('pjuu post #1', resp.get_data(as_text=True))
        self.assertIn('pjuu post #2', resp.get_data(as_text=True))
        self.assertIn('pjuu post #3', resp.get_data(as_text=True))

        self.assertNotIn('trusted post #1', resp.get_data(as_text=True))
        self.assertNotIn('trusted post #2', resp.get_data(as_text=True))
        self.assertNotIn('trusted post #3', resp.get_data(as_text=True))
