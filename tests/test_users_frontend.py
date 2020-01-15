# -*- coding: utf8 -*-

"""Users frontend tests.

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2020 Joe Doherty

"""

import io

from flask import url_for
import gridfs
import json

from pjuu import mongo as m
from pjuu.auth.backend import create_account, delete_account, activate
from pjuu.lib import keys as k, timestamp
from pjuu.posts.backend import create_post
from pjuu.users.backend import (
    follow_user, get_alerts, get_user, approve_user, is_trusted
)
from pjuu.users.views import timeify_filter, trusted_filter, follower_filter

from tests import FrontendTestCase


class FrontendTests(FrontendTestCase):
    """
    This test case will test all the users subpackages; views, decorators
    and forms
    """

    def test_feed_profile(self):
        """
        Feed has been tested else where. This is just a formal test of this.
        We will post a lot of posts as 2 users so we can trigger pagination
        etc, etc.
        """
        # Create 2 users and have them follow each other
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        user2 = create_account('user2', 'user2@pjuu.com', 'Password')
        activate(user1)
        activate(user2)
        follow_user(user1, user2)
        follow_user(user2, user1)

        # Both users are now following each other. Let's create 30 posts as
        # each user this will trigger a couple of Pagination pages on the feeds
        # and also trigger a page on the profile
        # We need to store a list of the pids since UUIDs became available
        posts = []
        for i in range(0, 51):
            posts.append(
                create_post(user1, 'user1', 'User 1, Post {}!'.format(i)))
            posts.append(
                create_post(user2, 'user1', 'User 2, Post {}!'.format(i)))
        # We now have 60 posts on each feed

        # Try and visit the feed when not logged in
        # We should see the landing page rendered
        # There is no flash message to check.
        resp = self.client.get(url_for('users.feed'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Welcome to Pjuu!', resp.get_data(as_text=True))

        # Log in as user 1 and check that they can see a couple of posts on the
        # first page
        resp = self.client.post(url_for('auth.signin'), data={
            'username': 'user1',
            'password': 'Password'
        }, follow_redirects=True)
        # This sends us too / (feed) by defaults
        self.assertEqual(resp.status_code, 200)
        self.assertIn('User 1, Post 50!', resp.get_data(as_text=True))
        self.assertIn('User 2, Post 50!', resp.get_data(as_text=True))
        # Makre sure posts more than 25 ago (default pagination break)
        self.assertNotIn('User 1, Post 1!', resp.get_data(as_text=True))
        self.assertNotIn('User 2, Post 1!', resp.get_data(as_text=True))
        # Check the pagination button for next is there are not prev
        self.assertIn('<!-- pagination:older -->', resp.get_data(as_text=True))
        self.assertIn('<!-- pagination:oldest -->',
                      resp.get_data(as_text=True))
        self.assertNotIn('<!-- pagination:newer -->',
                         resp.get_data(as_text=True))
        self.assertNotIn('<!-- pagination:newerest -->',
                         resp.get_data(as_text=True))

        # Let's go to page 2 in the pagination and check there are posts there
        resp = self.client.get(url_for('users.feed', page=2))

        # Check some posts are there and are not there
        self.assertIn('User 1, Post 30!', resp.get_data(as_text=True))
        self.assertIn('User 2, Post 30!', resp.get_data(as_text=True))
        self.assertNotIn('User 1, Post 10!', resp.get_data(as_text=True))
        self.assertNotIn('User 2, Post 5!', resp.get_data(as_text=True))
        # Check that both pagination buttons are there
        self.assertIn('<!-- pagination:older -->', resp.get_data(as_text=True))
        self.assertIn('<!-- pagination:oldest -->',
                      resp.get_data(as_text=True))
        self.assertIn('<!-- pagination:newer -->',
                      resp.get_data(as_text=True))
        self.assertIn('<!-- pagination:newest -->',
                      resp.get_data(as_text=True))

        # Let's go back to the first page
        resp = self.client.get(url_for('users.feed'))
        # We will delete one post and ensure that is goes missing
        self.assertIn('User 1, Post 50!', resp.get_data(as_text=True))
        # We won't check that the delete button belong to the above post
        # put we will check that there is at least one delete button
        self.assertIn('<!-- delete:post:', resp.get_data(as_text=True))
        # Delete the post
        resp = self.client.post(url_for('posts.delete_post', username='user1',
                                post_id=posts[100], next=url_for(
                                    'users.feed')),
                                follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('User 1, Post 49!', resp.get_data(as_text=True))
        self.assertNotIn('User 1, Post 50!', resp.get_data(as_text=True))

        # Check you can not go to a profile for a non-existant user
        resp = self.client.get(url_for('users.profile', username='None'))
        self.assertEqual(resp.status_code, 404)
        # Done for now

    def test_follow_unfollow(self):
        """
        Ensure users can follow and unfollow each other, also ensure that the
        followers and following pages show the correct value
        """
        # Create 2 users and have them follow each other
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        user2 = create_account('user2', 'user2@pjuu.com', 'Password')
        activate(user1)
        activate(user2)

        # Let's try and access the endpoints feature when we are not logged in
        # We should not be able to see it
        resp = self.client.post(url_for('users.follow', username='user1'),
                                follow_redirects=True)
        self.assertIn('You need to be signed in to view that',
                      resp.get_data(as_text=True))
        resp = self.client.post(url_for('users.unfollow', username='user1'),
                                follow_redirects=True)
        self.assertIn('You need to be signed in to view that',
                      resp.get_data(as_text=True))
        resp = self.client.get(url_for('users.following', username='user1'),
                               follow_redirects=True)
        self.assertIn('You need to be signed in to view that',
                      resp.get_data(as_text=True))
        resp = self.client.get(url_for('users.followers', username='user1'),
                               follow_redirects=True)
        self.assertIn('You need to be signed in to view that',
                      resp.get_data(as_text=True))

        # Ensure that test1 can follow and unfollow test2
        # Signin
        resp = self.client.post(url_for('auth.signin'), data={
            'username': 'user1',
            'password': 'Password'
        }, follow_redirects=True)
        self.assertIn('<h1>Feed</h1>', resp.get_data(as_text=True))

        # Try and see a non-existant users followers and following page
        resp = self.client.get(url_for('users.followers', username='None'))
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(url_for('users.following', username='None'))
        self.assertEqual(resp.status_code, 404)
        # Try follow and unfollow a non-existant user
        resp = self.client.post(url_for('users.follow', username='None'))
        self.assertEqual(resp.status_code, 404)
        resp = self.client.post(url_for('users.unfollow', username='None'))
        self.assertEqual(resp.status_code, 404)

        # Try follow and unfollow yourself
        resp = self.client.post(url_for('users.follow', username='user1'),
                                follow_redirects=True)
        self.assertIn('You can\'t follow/unfollow yourself',
                      resp.get_data(as_text=True))
        resp = self.client.post(url_for('users.unfollow', username='user1'),
                                follow_redirects=True)
        self.assertIn('You can\'t follow/unfollow yourself',
                      resp.get_data(as_text=True))

        # Visit test2 and ensure followers count is 0
        resp = self.client.get(url_for('users.followers', username='user2'))
        self.assertIn('<!-- followers:0 -->', resp.get_data(as_text=True))

        # Follow test2
        # Ensure we pass a next variable to come back to test2's followers page
        resp = self.client.post(url_for('users.follow', username='user2',
                                next=url_for('users.followers',
                                             username='user2')),
                                follow_redirects=True)
        # Ensure the flash message has informed use we are following
        self.assertIn('You have started following user2',
                      resp.get_data(as_text=True))
        # Ensure test2's followers count has been incremented
        self.assertIn('<!-- followers:1 -->', resp.get_data(as_text=True))
        # This should match inside a link (Test1 due to capitalization)
        # Not the best test but it works for now
        self.assertIn('<!-- list:user:{} -->'.format(user1),
                      resp.get_data(as_text=True))

        # Attempt to follow test2 again
        resp = self.client.post(url_for('users.follow', username='user2',
                                next=url_for('users.followers',
                                             username='user2')),
                                follow_redirects=True)
        # Check we got no confirmation
        self.assertNotIn('You have started following test2',
                         resp.get_data(as_text=True))
        # Check that the followers count has not incremented
        self.assertIn('<!-- followers:1 -->', resp.get_data(as_text=True))

        # Ensure test2 is in from YOUR (test1s) following page
        resp = self.client.get(url_for('users.following', username='user1'))
        self.assertNotIn('<!-- list:user:{} -->'.format(user1),
                         resp.get_data(as_text=True))

        # Unfollow test2
        # Ensure that all the previous has been reversed
        resp = self.client.post(url_for('users.unfollow', username='user2',
                                next=url_for('users.followers',
                                             username='user2')),
                                follow_redirects=True)
        self.assertIn('You are no longer following user2',
                      resp.get_data(as_text=True))
        self.assertIn('<!-- followers:0 -->', resp.get_data(as_text=True))
        # Check the list testing tag has gone
        self.assertNotIn('<!-- list:user:test1 -->',
                         resp.get_data(as_text=True))

        # Attempt to unfollow the user again
        resp = self.client.post(url_for('users.unfollow', username='user2',
                                next=url_for('users.followers',
                                             username='user2')),
                                follow_redirects=True)
        self.assertNotIn('You are no longer following user2',
                         resp.get_data(as_text=True))
        self.assertIn('<!-- followers:0 -->', resp.get_data(as_text=True))

        # Ensure test2 is missing from YOUR (test1s) following page
        resp = self.client.get(url_for('users.following', username='user1'))
        self.assertNotIn('<!-- list:user:{} -->'.format(user2),
                         resp.get_data(as_text=True))
        # Done for now

    def test_approve_unapprove(self):
        """Ensure the user can approve and un-approve users"""
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        user2 = create_account('user2', 'user2@pjuu.com', 'Password')
        user3 = create_account('user3', 'user3@pjuu.com', 'Password')
        activate(user1)
        activate(user2)
        activate(user3)

        # User 2 is the only user following user1
        follow_user(user2, user1)

        resp = self.client.post(url_for('auth.signin'), data={
            'username': 'user1',
            'password': 'Password'
        })

        resp = self.client.get(url_for('users.followers', username='user1'),
                               follow_redirects=True)
        self.assertIn('<!-- list:user:{} -->'.format(user2),
                      resp.get_data(as_text=True))
        self.assertIn(url_for('users.approve', username='user2'),
                      resp.get_data(as_text=True))

        # Approve user2
        resp = self.client.post(url_for('users.approve', username='user2'),
                                follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(url_for('users.unapprove', username='user2'),
                      resp.get_data(as_text=True))

        # Unapprove user2
        resp = self.client.post(url_for('users.unapprove', username='user2'),
                                follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(url_for('users.approve', username='user2'),
                      resp.get_data(as_text=True))

        # Try to unapprove user2 again
        resp = self.client.post(url_for('users.unapprove', username='user2'),
                                follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('You can\'t untrust a user who is not trusted',
                      resp.get_data(as_text=True))

        # Try and approve a user who is not following you
        resp = self.client.post(url_for('users.approve', username='user3'),
                                follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('You can\'t trust a user who is not following you',
                      resp.get_data(as_text=True))

        # Try again but you are following the user (wont-work)
        follow_user(user1, user3)
        resp = self.client.post(url_for('users.approve', username='user3'),
                                follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('You can\'t trust a user who is not following you',
                      resp.get_data(as_text=True))

        # Try and approve yourself
        resp = self.client.post(url_for('users.approve', username='user1'),
                                follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('You should already trust yourself ;-P',
                      resp.get_data(as_text=True))

        # Try and unapprove self
        resp = self.client.post(url_for('users.unapprove', username='user1'),
                                follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('You can\'t untrust your self',
                      resp.get_data(as_text=True))

        # Try and approve/unapprove a user that doesn't exist
        resp = self.client.post(url_for('users.approve', username='user5'),
                                follow_redirects=True)
        self.assertEqual(resp.status_code, 404)
        resp = self.client.post(url_for('users.unapprove', username='user5'),
                                follow_redirects=True)
        self.assertEqual(resp.status_code, 404)

    def test_search(self):
        """Ensure the search works and users are shown correctly."""
        # Let's try and access the endpoint feature when we are not logged in
        # We should not be able to see it
        resp = self.client.get(url_for('users.search'), follow_redirects=True)
        self.assertIn('You need to be signed in to view that',
                      resp.get_data(as_text=True))

        # We need some users with usernames different enough that we can test
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        user2 = create_account('user2', 'user2@pjuu.com', 'Password')
        user3 = create_account('joe', 'joe@pjuu.com', 'Password')
        user4 = create_account('ant', 'ant@pjuu.com', 'Password')
        user5 = create_account('fil', 'fil@pjuu.com', 'Password')
        # Activate some of the accounts.
        activate(user1)
        activate(user2)
        activate(user3)
        activate(user4)

        # Let's sign in!
        # We will sign in as joe this time as that is me :)
        self.client.post('signin', data={
            'username': 'joe',
            'password': 'Password'
        })

        # Let's check we see the correct thing on the search page when there
        # is no search
        resp = self.client.get(url_for('users.search'))
        self.assertIn('<!-- author search -->', resp.get_data(as_text=True))
        self.assertNotIn('<h1>Results:', resp.get_data(as_text=True))

        # Lets search for ourselves
        resp = self.client.get(url_for('users.search', query='joe'))
        self.assertIn('<!-- list:user:{} -->'.format(user3),
                      resp.get_data(as_text=True))

        # Lets check that this is case-insensitive
        resp = self.client.get(url_for('users.search', query='JOE'))
        self.assertIn('<!-- list:user:{} -->'.format(user3),
                      resp.get_data(as_text=True))

        # Lets try this partially
        resp = self.client.get(url_for('users.search', query='j'))
        self.assertIn('<!-- list:user:{} -->'.format(user3),
                      resp.get_data(as_text=True))

        # Lets check we see two users if two match
        resp = self.client.get(url_for('users.search', query='user'))
        self.assertIn('<!-- list:user:{} -->'.format(user1),
                      resp.get_data(as_text=True))
        self.assertIn('<!-- list:user:{} -->'.format(user2),
                      resp.get_data(as_text=True))

        # Lets check to see if inactive users show up. THEY SHOULD
        resp = self.client.get(url_for('users.search', query='fil'))
        self.assertNotIn('<!-- list:user:{} -->'.format(user5),
                         resp.get_data(as_text=True))

        # Lets check that we can find ant because we are going to delete him
        # to ensure he goes! This has caused issues on the live site
        resp = self.client.get(url_for('users.search', query='ant'))
        self.assertIn('<!-- list:user:{} -->'.format(user4),
                      resp.get_data(as_text=True))

        # Lets check that we can find ant because we are going to delete him
        # to ensure he goes! This has caused issues on the live site
        resp = self.client.get(url_for('users.search', query='ant'))
        self.assertIn('<!-- list:user:{} -->'.format(user4),
                      resp.get_data(as_text=True))

        # We will just backend delete the account.
        delete_account(user4)
        # Account is gone, lets ensure this has gone
        resp = self.client.get(url_for('users.search', query='ant'))
        self.assertNotIn('<!-- list:user:{} -->'.format(user4),
                         resp.get_data(as_text=True))
        # Done for now!

    def test_avatars_hashtag_search(self):
        """Ensure user avatars appear when searching for posts with a hashtag
        """
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        # Activate it
        activate(user1)

        # Signin
        self.client.post(url_for('auth.signin'), data={
            'username': 'user1',
            'password': 'Password'
        })

        # Ensure user avatar appear in the search when searching for hashtags
        image = io.BytesIO(
            open('tests/upload_test_files/otter.jpg', 'rb').read())

        self.client.post(url_for('users.settings_profile'), data={
            'upload': (image, 'otter.png')
        }, follow_redirects=True)

        # Get the user so we can see if the avatar is appearing
        user = get_user(user1)

        # Create a post to search for
        post1 = create_post(user1, 'user1', 'Hello #pjuuie\'s')

        resp = self.client.get(url_for('users.search', query='#pjuuie'))
        self.assertIn('<!-- list:post:{} -->'.format(post1),
                      resp.get_data(as_text=True))
        self.assertIn(url_for('posts.get_upload', filename=user.get('avatar')),
                      resp.get_data(as_text=True))

    def test_settings_profile(self):
        """Ensure users have the ability to see some information about there
        account and can change there about message and display options.
        """
        # Let's try and access the endpoint feature when we are not logged in
        # We should not be able to see it
        resp = self.client.get(url_for('users.settings_profile'),
                               follow_redirects=True)
        self.assertIn('You need to be signed in to view that',
                      resp.get_data(as_text=True))

        # Create a test user
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        # Activate it
        activate(user1)

        # Signin
        self.client.post(url_for('auth.signin'), data={
            'username': 'user1',
            'password': 'Password'
        })

        # If the user profile hasn't been saved the sort order should
        user = m.db.users.find_one({'username': 'user1'})
        self.assertIsNone(user.get('reply_sort_order'))

        # Go to our settings page and ensure everything is there
        resp = self.client.get(url_for('users.settings_profile'))
        self.assertIn('<div class="content">user1</div>',
                      resp.get_data(as_text=True))
        self.assertIn('<div class="content">user1@pjuu.com</div>',
                      resp.get_data(as_text=True))
        # Post to the form and update our about. We should also be this on
        # this page
        resp = self.client.post(url_for('users.settings_profile'), data={
            'about': 'Otters love fish!'
        }, follow_redirects=True)
        self.assertIn('Otters love fish!', resp.get_data(as_text=True))

        # Try posting a MASSIVE about ('Otter' * 100)
        resp = self.client.post(url_for('users.settings_profile'), data={
            'about': 'Otters' * 100
        }, follow_redirects=True)
        # Check we get the form error
        self.assertIn('Oh no! There are errors in your form',
                      resp.get_data(as_text=True))
        # Ensure the about did not change
        self.assertIn('Otters love fish!', resp.get_data(as_text=True))

        resp = self.client.post(url_for('users.settings_profile'), data={
            'about': 'Test display settings',
            'hide_feed_images': True,
        }, follow_redirects=True)
        self.assertIn('Test display settings', resp.get_data(as_text=True))

        # Not sure it's good to check for a checked checkbox so test the user
        # account
        user = get_user(user1)
        self.assertTrue(user.get('hide_feed_images'))

        # Ensure you can unset it
        resp = self.client.post(url_for('users.settings_profile'), data={
            'about': 'Test display settings',
        }, follow_redirects=True)

        # Get the user again. This should have been updated from the database
        user = get_user(user1)
        self.assertFalse(user.get('hide_feed_images'))

        # Test setting a homepage and location works as expected
        resp = self.client.post(url_for('users.settings_profile'), data={
            'about': 'Test display settings',
            'homepage': 'pjuu.com',
            'location': 'England'
        }, follow_redirects=True)

        user = get_user(user1)
        self.assertEqual(user.get('homepage'), 'http://pjuu.com')
        self.assertEqual(user.get('location'), 'England')

        # Ensure you can't set an invalid URL
        resp = self.client.post(url_for('users.settings_profile'), data={
            'about': 'Test display settings',
            'homepage': 'pjuu.cheese',
        }, follow_redirects=True)

        self.assertIn('Please ensure the home page is a valid URL or empty',
                      resp.get_data(as_text=True))

        # Test a URL that doesn't need to be prefixed
        resp = self.client.post(url_for('users.settings_profile'), data={
            'about': 'Test display settings',
            'homepage': 'https://pjuu.com',
        }, follow_redirects=True)

        user = get_user(user1)
        self.assertEqual(user.get('homepage'), 'https://pjuu.com')

        resp = self.client.post(url_for('users.settings_profile'), data={
            'homepage': 'https://pjuu.com',
            'location': 'England',
        }, follow_redirects=True)

        # Ensure the users profile reflects the changes
        resp = self.client.get(url_for('users.profile', username='user1'))
        self.assertIn('<i class="fa fa-map-marker fa-lg"></i> England',
                      resp.get_data(as_text=True))
        self.assertIn(
            '<a href="https://pjuu.com"><i class="fa fa-globe fa-lg"></i></a>',
            resp.get_data(as_text=True))

        # If the view before has been saved the default is -1 (unchecked)
        user = m.db.users.find_one({'username': 'user1'})
        self.assertEqual(user.get('reply_sort_order'), -1)

        resp = self.client.post(url_for('users.settings_profile'), data={
            'reply_sort_order': True,
        }, follow_redirects=True)
        user = m.db.users.find_one({'username': 'user1'})
        self.assertEqual(user.get('reply_sort_order'), 1)

        # You can not post the field as thats classed as a True value
        resp = self.client.post(url_for('users.settings_profile'),
                                data={'about': 'Test'},
                                follow_redirects=True)
        user = m.db.users.find_one({'username': 'user1'})
        self.assertEqual(user.get('reply_sort_order'), -1)

    def test_alerts(self):
        """Check that alerts are displayed properly in the frontend."""
        # Create two test users
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        user2 = create_account('user2', 'user2@pjuu.com', 'Password')
        user3 = create_account('user3', 'user3@pjuu.com', 'Password')
        # Activate
        activate(user1)
        activate(user2)
        activate(user3)

        # Try an visit i-has-alerts when not logged in
        resp = self.client.get(url_for('users.new_alerts'))
        self.assertEqual(resp.status_code, 403)

        # Login as user1
        self.client.post(url_for('auth.signin'), data={
            'username': 'user1',
            'password': 'Password'
        })

        # Get I has alerts and check that it is false
        resp = self.client.get(url_for('users.new_alerts'))
        # Check the JSON response
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            json.loads(resp.get_data(as_text=True)).get('new_alerts'), 0)

        # Ensure that /alerts returns nothing
        resp = self.client.get(url_for('users.alerts'))
        self.assertNotIn('list:alert', resp.get_data(as_text=True))
        self.assertIn('Empty', resp.get_data(as_text=True))

        # Get user2 to follow user1
        follow_user(user2, user1)

        # Ensure that /i-has-alerts is correct
        resp = self.client.get(url_for('users.new_alerts'))
        # Check the JSON response
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            json.loads(resp.get_data(as_text=True)).get('new_alerts'), 1)

        # Ensure the count goes up correctly
        follow_user(user3, user1)

        resp = self.client.get(url_for('users.new_alerts'))
        # Check the JSON response
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            json.loads(resp.get_data(as_text=True)).get('new_alerts'), 2)

        resp = self.client.get(url_for('users.alerts'))
        # We don't know the alert ID but we can check that one is there by
        # looking for the comment in test mode
        self.assertIn('list:alert:', resp.get_data(as_text=True))
        self.assertNotIn('Empty', resp.get_data(as_text=True))
        # Check test2's name is there
        self.assertIn('user2', resp.get_data(as_text=True))
        # Check that the prettify message from FollowAlert is there
        self.assertIn('has started following you', resp.get_data(as_text=True))

        # We have now checked the alerts, ensure that i-has-alerts is False
        resp = self.client.get(url_for('users.new_alerts'))
        # Check the JSON response
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            json.loads(resp.get_data(as_text=True)).get('new_alerts'), 0)

        # Check that we can delete the alert
        # Get the both alert ids from the backend function
        alert1 = get_alerts(user1).items[0].alert_id
        alert2 = get_alerts(user1).items[1].alert_id

        # Check that we don't get a message if there was no alert to delete
        resp = self.client.get(url_for('users.delete_alert',
                                       alert_id=k.NIL_VALUE),
                               follow_redirects=True)
        self.assertNotIn('Alert has been hidden', resp.get_data(as_text=True))

        # Delete both alerts
        resp = self.client.get(url_for('users.delete_alert', alert_id=alert1),
                               follow_redirects=True)
        self.assertIn('Alert has been hidden', resp.get_data(as_text=True))
        self.assertNotIn('<!-- list:alert:{} -->'.format(alert1),
                         resp.get_data(as_text=True))
        self.assertIn('<!-- list:alert:{} -->'.format(alert2),
                      resp.get_data(as_text=True))

        # Check when the last alert is deleted we get an empty list
        resp = self.client.get(url_for('users.delete_alert', alert_id=alert2),
                               follow_redirects=True)
        self.assertIn('Alert has been hidden', resp.get_data(as_text=True))
        # Check that there are also no alerts now
        self.assertIn('Empty', resp.get_data(as_text=True))

        # Done for now

    def test_timeify_filter(self):
        """Test the timeify filter

        """
        self.assertEqual(timeify_filter(timestamp()), 'Less than a second ago')
        # Check one year ago
        time_yearago = timestamp() - 31536000
        self.assertEqual(timeify_filter(time_yearago), '1 year ago')
        # Check two months ago
        time_yearago = timestamp() - 5184000
        self.assertEqual(timeify_filter(time_yearago), '2 months ago')
        # Check 3 weeks ago
        time_yearago = timestamp() - 1814400
        self.assertEqual(timeify_filter(time_yearago), '3 weeks ago')

    def test_remove_from_feed(self):
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        user2 = create_account('user2', 'user2@pjuu.com', 'Password')
        # Activate
        activate(user1)

        follow_user(user1, user2)

        post = create_post(user2, 'user2', 'User 2, is here')

        # Check that the post appears in the users feed
        resp = self.client.post(url_for('auth.signin'), data={
            'username': 'user1',
            'password': 'Password'
        }, follow_redirects=True)

        self.assertIn('User 2, is here', resp.get_data(as_text=True))
        self.assertIn('remove:post:{}'.format(post),
                      resp.get_data(as_text=True))

        # Hide the post
        resp = self.client.post(url_for('users.remove_from_feed',
                                        post_id=post),
                                follow_redirects=True)

        self.assertNotIn('User 2, is here', resp.get_data(as_text=True))
        self.assertNotIn('remove:post:{}'.format(post),
                         resp.get_data(as_text=True))
        self.assertIn('Message has been removed from feed',
                      resp.get_data(as_text=True))

        # Can a user remove their own post?
        post = create_post(user1, 'user1', 'User 1, is here')

        # The user should not see a hide button though
        resp = self.client.get(url_for('users.feed'))
        self.assertIn('User 1, is here', resp.get_data(as_text=True))
        self.assertNotIn('remove:post:{}'.format(post),
                         resp.get_data(as_text=True))

        # Ensure the URL hides the post
        resp = self.client.post(url_for('users.remove_from_feed',
                                        post_id=post),
                                follow_redirects=True)

        self.assertNotIn('User 1, is here', resp.get_data(as_text=True))
        self.assertIn('Message has been removed from feed',
                      resp.get_data(as_text=True))

        # Ensure removing a post that is not in your feed does not displau a
        # flash message
        resp = self.client.post(url_for('users.remove_from_feed',
                                        post_id=''),
                                follow_redirects=True)

        self.assertNotIn('Message has been removed from feed',
                         resp.get_data(as_text=True))

    def test_avatars(self):
        """Can a user set there own avatar?"""
        # Create a test user
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        # Activate it
        activate(user1)

        # Signin
        self.client.post(url_for('auth.signin'), data={
            'username': 'user1',
            'password': 'Password'
        })

        # Check default avatar is present
        resp = self.client.get(url_for('users.settings_profile',
                               username='user1'))
        self.assertIn('<!-- user:avatar:default -->',
                      resp.get_data(as_text=True))
        self.assertIn(
            url_for('static', filename='img/otter_avatar.png'),
            resp.get_data(as_text=True))

        # Check the avatar for the default
        # We can't inspect it
        user = get_user(user1)
        resp = self.client.get(url_for('static',
                                       filename='img/otter_avatar.png'))
        self.assertEqual(resp.status_code, 200)

        # Get the users object to check some things
        user = get_user(user1)

        # User shouldn't have an avatar
        self.assertIsNone(user.get('avatar'))

        # Create the file
        image = io.BytesIO(
            open('tests/upload_test_files/otter.jpg', 'rb').read())

        resp = self.client.post(url_for('users.settings_profile'), data={
            'upload': (image, 'otter.png')
        }, follow_redirects=True)

        user = get_user(user1)

        self.assertIsNotNone(user.get('avatar'))
        self.assertIn('<!-- user:avatar:{} -->'.format(user.get('avatar')),
                      resp.get_data(as_text=True))

        grid = gridfs.GridFS(m.db, collection='uploads')
        self.assertEqual(
            grid.find({'filename': user.get('avatar')}).count(), 1)

        resp = self.client.get(url_for('posts.get_upload',
                               filename=user.get('avatar')))
        self.assertEqual(resp.status_code, 200)

        # upload another and ensure there is only one in GridFs
        image = io.BytesIO(
            open('tests/upload_test_files/otter.jpg', 'rb').read())

        resp = self.client.post(url_for('users.settings_profile'), data={
            'upload': (image, 'otter.png')
        }, follow_redirects=True)

        user = get_user(user1)
        self.assertEqual(grid.find({'filename': user.get('avatar')}).count(),
                         1)

        # This is technically an auth test but if we delete the account we can
        # ensure the avatar is removed.
        delete_account(user1)
        self.assertEqual(grid.find({'filename': user.get('avatar')}).count(),
                         0)

    def test_permissions(self):
        """Ensure only users with the correct permissions can see posts"""
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        activate(user1)
        post1 = create_post(user1, 'user1', 'Test public', permission=0)
        post2 = create_post(user1, 'user1', 'Test pjuu', permission=1)
        post3 = create_post(user1, 'user1', 'Test approved', permission=2)

        resp = self.client.get(url_for('users.profile', username='user1'))
        self.assertIn('Test public', resp.get_data(as_text=True))
        self.assertNotIn('Test pjuu', resp.get_data(as_text=True))
        self.assertNotIn('Test approved', resp.get_data(as_text=True))

        resp = self.client.get(url_for('posts.view_post', username='user1',
                                       post_id=post1))
        self.assertEqual(resp.status_code, 200)

        resp = self.client.get(url_for('posts.view_post', username='user1',
                                       post_id=post2))
        self.assertEqual(resp.status_code, 403)

        resp = self.client.get(url_for('posts.view_post', username='user1',
                                       post_id=post3))
        self.assertEqual(resp.status_code, 403)

        # Create a user and check we can see the Pjuu-wide post
        user2 = create_account('user2', 'user2@pjuu.com', 'Password')
        activate(user2)

        self.client.post(url_for('auth.signin'), data={
            'username': 'user2',
            'password': 'Password'
        })
        resp = self.client.get(url_for('users.profile', username='user1'))
        self.assertIn('Test public', resp.get_data(as_text=True))
        self.assertIn('Test pjuu', resp.get_data(as_text=True))
        self.assertNotIn('Test approved', resp.get_data(as_text=True))

        resp = self.client.get(url_for('posts.view_post', username='user1',
                                       post_id=post1))
        self.assertEqual(resp.status_code, 200)

        resp = self.client.get(url_for('posts.view_post', username='user1',
                                       post_id=post2))
        self.assertEqual(resp.status_code, 200)

        resp = self.client.get(url_for('posts.view_post', username='user1',
                                       post_id=post3))
        self.assertEqual(resp.status_code, 403)

        # Have user1 approve user2 and ensure he can see all posts
        # User2 needs to be following user1
        follow_user(user2, user1)
        approve_user(user1, user2)
        self.assertTrue(is_trusted(user1, user2))

        resp = self.client.get(url_for('users.profile', username='user1'))
        self.assertIn('Test public', resp.get_data(as_text=True))
        self.assertIn('Test pjuu', resp.get_data(as_text=True))
        self.assertIn('Test approved', resp.get_data(as_text=True))

        resp = self.client.get(url_for('posts.view_post', username='user1',
                                       post_id=post1))
        self.assertEqual(resp.status_code, 200)

        resp = self.client.get(url_for('posts.view_post', username='user1',
                                       post_id=post2))
        self.assertEqual(resp.status_code, 200)

        resp = self.client.get(url_for('posts.view_post', username='user1',
                                       post_id=post3))
        self.assertEqual(resp.status_code, 200)

    def test_tip_system(self):
        """Ensure tips show when they are set to and they can be hidden
        and reset as needs
        """
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        activate(user1)
        self.client.post(url_for('auth.signin'), data={
            'username': 'user1',
            'password': 'Password'
        })

        # Ensure the tip shows for new users
        resp = self.client.get(url_for('users.feed'))
        self.assertIn('tip:welcome', resp.get_data(as_text=True))
        self.assertIn(url_for('users.hide_tip', tip_name='welcome'),
                      resp.get_data(as_text=True))

        # Ensure we can hide the tip
        resp = self.client.post(url_for('users.hide_tip', tip_name='welcome'),
                                follow_redirects=True)
        self.assertNotIn('tip:welcome', resp.get_data(as_text=True))
        self.assertNotIn(url_for('users.hide_tip', tip_name='welcome'),
                         resp.get_data(as_text=True))

        # Ensure resetting the tips shows them again
        resp = self.client.post(url_for('users.reset_tips', tip_name='welcome',
                                        next=url_for('users.feed')),
                                follow_redirects=True)
        self.assertIn('tip:welcome', resp.get_data(as_text=True))
        self.assertIn(url_for('users.hide_tip', tip_name='welcome'),
                      resp.get_data(as_text=True))

        # Try and remove a tip that isn't valid
        resp = self.client.post(url_for('users.hide_tip', tip_name='cheese'),
                                follow_redirects=True)
        self.assertEqual(resp.status_code, 404)

    def test_new_trusted_buttons_profile(self):
        """Ensure the new trusted buttons work on a users profile"""
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        user2 = create_account('user2', 'user2@pjuu.com', 'Password')
        user3 = create_account('user3', 'user2@pjuu.com', 'Password')

        activate(user1)
        activate(user2)
        activate(user3)

        # Test the 2 filters just so we know they work.
        # This is a bit of a cheat they are NEVER used when logged out.
        self.assertEqual(trusted_filter("None"), False)
        self.assertEqual(follower_filter("None"), False)

        # Check that the profile trust button does not show if you are not
        # logged in
        resp = self.client.get(url_for('users.profile', username='user1'))
        self.assertNotIn('trust:{}'.format(user1),
                         resp.get_data(as_text=True))
        self.assertNotIn('untrust:{}'.format(user1),
                         resp.get_data(as_text=True))

        # Ensure we can't see a users trusted list
        # Should be redirected to login (we will test Forbidden)
        resp = self.client.get(url_for('users.trusted', username='user1'))
        self.assertEqual(resp.status_code, 302)

        # Check that neither of the buttons appear if the user is not following
        self.client.post(url_for('auth.signin'), data={
            'username': 'user1',
            'password': 'Password'
        })
        resp = self.client.get(url_for('users.profile', username='user2'))
        self.assertNotIn('trust:{}'.format(user1), resp.get_data(as_text=True))
        self.assertNotIn('untrust:{}'.format(user1),
                         resp.get_data(as_text=True))

        # user2 follows user1
        follow_user(user2, user1)

        resp = self.client.get(url_for('users.profile', username='user2'))
        self.assertIn('<!-- trust:{} -->'.format(user2),
                      resp.get_data(as_text=True))
        self.assertNotIn('<!-- untrust:{} -->'.format(user2),
                         resp.get_data(as_text=True))

        # Ensure a trust count is none on our own profile
        resp = self.client.get(url_for('users.profile', username='user1'))
        self.assertIn('trusted:0', resp.get_data(as_text=True))

        # Ensure user2 is not in our trusted list
        resp = self.client.get(url_for('users.trusted', username='user1'))
        self.assertNotIn('list:user:{}'.format(user2),
                         resp.get_data(as_text=True))

        # user1 trusts user2
        approve_user(user1, user2)
        self.assertTrue(is_trusted(user1, user2))

        resp = self.client.get(url_for('users.profile', username='user2'))
        self.assertIn('<!-- untrust:{} -->'.format(user2),
                      resp.get_data(as_text=True))
        self.assertNotIn('<!-- trust:{} -->'.format(user2),
                         resp.get_data(as_text=True))

        # Ensure our trust count has incremented
        resp = self.client.get(url_for('users.profile', username='user1'))
        self.assertIn('trusted:1', resp.get_data(as_text=True))

        # Ensure user2 appears in our trusted list
        resp = self.client.get(url_for('users.trusted', username='user1'))
        self.assertIn('list:user:{}'.format(user2),
                      resp.get_data(as_text=True))

        # Ensure we can't see user2's trusted list
        resp = self.client.get(url_for('users.trusted', username='user2'))
        self.assertEqual(resp.status_code, 403)

        # Attempt to look at the trusted for a non-existant user
        resp = self.client.get(url_for('users.trusted', username='user0'))
        self.assertEqual(resp.status_code, 404)
