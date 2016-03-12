# -*- coding: utf8 -*-

"""Users frontend tests.

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2016 Joe Doherty

"""

import io

from flask import url_for
import gridfs
import json

from pjuu import mongo as m
from pjuu.auth.backend import create_account, delete_account, activate
from pjuu.lib import keys as k, timestamp
from pjuu.posts.backend import create_post
from pjuu.users.backend import follow_user, get_alerts, get_user
from pjuu.users.views import timeify_filter

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
            posts.append(create_post(user1, 'user1', 'User 1, Post %d!' % i))
            posts.append(create_post(user2, 'user1', 'User 2, Post %d!' % i))
        # We now have 60 posts on each feed

        # Try and visit the feed when not logged in
        # There is no flash message to check.
        resp = self.client.get(url_for('users.feed'))
        self.assertEqual(resp.status_code, 302)

        # Log in as user 1 and check that they can see a couple of posts on the
        # first page
        resp = self.client.post(url_for('auth.signin'), data={
            'username': 'user1',
            'password': 'Password'
        }, follow_redirects=True)
        # This sends us too / (feed) by defaults
        self.assertEqual(resp.status_code, 200)
        self.assertIn('User 1, Post 50!', resp.data)
        self.assertIn('User 2, Post 50!', resp.data)
        # Makre sure posts more than 25 ago (default pagination break)
        self.assertNotIn('User 1, Post 1!', resp.data)
        self.assertNotIn('User 2, Post 1!', resp.data)
        # Check the pagination button for next is there are not prev
        self.assertIn('<!-- pagination:older -->', resp.data)
        self.assertIn('<!-- pagination:oldest -->', resp.data)
        self.assertNotIn('<!-- pagination:newer -->', resp.data)
        self.assertNotIn('<!-- pagination:newerest -->', resp.data)

        # Let's go to page 2 in the pagination and check there are posts there
        resp = self.client.get(url_for('users.feed', page=2))

        # Check some posts are there and are not there
        self.assertIn('User 1, Post 30!', resp.data)
        self.assertIn('User 2, Post 30!', resp.data)
        self.assertNotIn('User 1, Post 10!', resp.data)
        self.assertNotIn('User 2, Post 5!', resp.data)
        # Check that both pagination buttons are there
        self.assertIn('<!-- pagination:older -->', resp.data)
        self.assertIn('<!-- pagination:oldest -->', resp.data)
        self.assertIn('<!-- pagination:newer -->', resp.data)
        self.assertIn('<!-- pagination:newest -->', resp.data)

        # Let's go back to the first page
        resp = self.client.get(url_for('users.feed'))
        # We will delete one post and ensure that is goes missing
        self.assertIn('User 1, Post 50!', resp.data)
        # We won't check that the delete button belong to the above post
        # put we will check that there is at least one delete button
        self.assertIn('<!-- delete:post:', resp.data)
        # Delete the post
        resp = self.client.post(url_for('posts.delete_post', username='user1',
                                post_id=posts[100], next=url_for(
                                    'users.feed')),
                                follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('User 1, Post 49!', resp.data)
        self.assertNotIn('User 1, Post 50!', resp.data)

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
        self.assertIn('You need to be logged in to view that', resp.data)
        resp = self.client.post(url_for('users.unfollow', username='user1'),
                                follow_redirects=True)
        self.assertIn('You need to be logged in to view that', resp.data)
        resp = self.client.get(url_for('users.following', username='user1'),
                               follow_redirects=True)
        self.assertIn('You need to be logged in to view that', resp.data)
        resp = self.client.get(url_for('users.followers', username='user1'),
                               follow_redirects=True)
        self.assertIn('You need to be logged in to view that', resp.data)

        # Ensure that test1 can follow and unfollow test2
        # Signin
        resp = self.client.post(url_for('auth.signin'), data={
            'username': 'user1',
            'password': 'Password'
        }, follow_redirects=True)
        self.assertIn('<h1>Feed</h1>', resp.data)

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
        self.assertIn('You can\'t follow/unfollow yourself', resp.data)
        resp = self.client.post(url_for('users.unfollow', username='user1'),
                                follow_redirects=True)
        self.assertIn('You can\'t follow/unfollow yourself', resp.data)

        # Visit test2 and ensure followers count is 0
        resp = self.client.get(url_for('users.followers', username='user2'))
        self.assertIn('<!-- followers:0 -->', resp.data)

        # Follow test2
        # Ensure we pass a next variable to come back to test2's followers page
        resp = self.client.post(url_for('users.follow', username='user2',
                                next=url_for('users.followers',
                                             username='user2')),
                                follow_redirects=True)
        # Ensure the flash message has informed use we are following
        self.assertIn('You have started following user2', resp.data)
        # Ensure test2's followers count has been incremented
        self.assertIn('<!-- followers:1 -->', resp.data)
        # This should match inside a link (Test1 due to capitalization)
        # Not the best test but it works for now
        self.assertIn('<!-- list:user:%s -->' % user1, resp.data)

        # Attempt to follow test2 again
        resp = self.client.post(url_for('users.follow', username='user2',
                                next=url_for('users.followers',
                                             username='user2')),
                                follow_redirects=True)
        # Check we got no confirmation
        self.assertNotIn('You have started following test2', resp.data)
        # Check that the followers count has not incremented
        self.assertIn('<!-- followers:1 -->', resp.data)

        # Ensure test2 is in from YOUR (test1s) following page
        resp = self.client.get(url_for('users.following', username='user1'))
        self.assertNotIn('<!-- list:user:%s -->' % user1, resp.data)

        # Unfollow test2
        # Ensure that all the previous has been reversed
        resp = self.client.post(url_for('users.unfollow', username='user2',
                                next=url_for('users.followers',
                                             username='user2')),
                                follow_redirects=True)
        self.assertIn('You are no longer following user2', resp.data)
        self.assertIn('<!-- followers:0 -->', resp.data)
        # Check the list testing tag has gone
        self.assertNotIn('<!-- list:user:test1 -->', resp.data)

        # Attempt to unfollow the user again
        resp = self.client.post(url_for('users.unfollow', username='user2',
                                next=url_for('users.followers',
                                             username='user2')),
                                follow_redirects=True)
        self.assertNotIn('You are no longer following user2', resp.data)
        self.assertIn('<!-- followers:0 -->', resp.data)

        # Ensure test2 is missing from YOUR (test1s) following page
        resp = self.client.get(url_for('users.following', username='user1'))
        self.assertNotIn('<!-- list:user:%s -->' % user2, resp.data)
        # Done for now

    def test_search(self):
        """
        Ensure the search works and users are shown correctly.
        """
        # Let's try and access the endpoint feature when we are not logged in
        # We should not be able to see it
        resp = self.client.get('users.search', follow_redirects=True)
        self.assertIn('You need to be logged in to view that', resp.data)

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
        self.assertIn('<!-- author search -->', resp.data)
        self.assertNotIn('<h1>Results:', resp.data)

        # Lets search for ourselves
        resp = self.client.get(url_for('users.search', query='joe'))
        self.assertIn('<!-- list:user:%s -->' % user3, resp.data)

        # Lets check that this is case-insensitive
        resp = self.client.get(url_for('users.search', query='JOE'))
        self.assertIn('<!-- list:user:%s -->' % user3, resp.data)

        # Lets try this partially
        resp = self.client.get(url_for('users.search', query='j'))
        self.assertIn('<!-- list:user:%s -->' % user3, resp.data)

        # Lets check we see two users if two match
        resp = self.client.get(url_for('users.search', query='user'))
        self.assertIn('<!-- list:user:%s -->' % user1, resp.data)
        self.assertIn('<!-- list:user:%s -->' % user2, resp.data)

        # Lets check to see if inactive users show up. THEY SHOULD
        resp = self.client.get(url_for('users.search', query='fil'))
        self.assertNotIn('<!-- list:user:%s -->' % user5, resp.data)

        # Lets check that we can find ant because we are going to delete him
        # to ensure he goes! This has caused issues on the live site
        resp = self.client.get(url_for('users.search', query='ant'))
        self.assertIn('<!-- list:user:%s -->' % user4, resp.data)

        # We will just backend delete the account.
        delete_account(user4)
        # Account is gone, lets ensure this has gone
        resp = self.client.get(url_for('users.search', query='ant'))
        self.assertNotIn('<!-- list:user:%s -->' % user4, resp.data)
        # Done for now!

    def test_settings_profile(self):
        """Ensure users have the ability to see some information about there
        account and can change there about message and display options.
        """
        # Let's try and access the endpoint feature when we are not logged in
        # We should not be able to see it
        resp = self.client.get('settings_profile', follow_redirects=True)
        self.assertIn('You need to be logged in to view that', resp.data)

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
        self.assertIn('<div class="content">user1</div>', resp.data)
        self.assertIn('<div class="content">user1@pjuu.com</div>', resp.data)
        # Post to the form and update our about. We should also be this on
        # this page
        resp = self.client.post(url_for('users.settings_profile'), data={
            'about': 'Otters love fish!'
        }, follow_redirects=True)
        self.assertIn('Otters love fish!', resp.data)

        # Try posting a MASSIVE about ('Otter' * 100)
        resp = self.client.post(url_for('users.settings_profile'), data={
            'about': 'Otters' * 100
        }, follow_redirects=True)
        # Check we get the form error
        self.assertIn('Oh no! There are errors in your form', resp.data)
        # Ensure the about did not change
        self.assertIn('Otters love fish!', resp.data)

        resp = self.client.post(url_for('users.settings_profile'), data={
            'about': 'Test display settings',
            'hide_feed_images': True,
        }, follow_redirects=True)
        self.assertIn('Test display settings', resp.data)

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
                      resp.data)

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
                      resp.data)
        self.assertIn(
            '<a href="https://pjuu.com"><i class="fa fa-globe fa-lg"></i></a>',
            resp.data)

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
        self.assertEqual(json.loads(resp.data).get('new_alerts'), 0)

        # Ensure that /alerts returns nothing
        resp = self.client.get(url_for('users.alerts'))
        self.assertNotIn('list:alert', resp.data)
        self.assertIn('Empty', resp.data)

        # Get user2 to follow user1
        follow_user(user2, user1)

        # Ensure that /i-has-alerts is correct
        resp = self.client.get(url_for('users.new_alerts'))
        # Check the JSON response
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.data).get('new_alerts'), 1)

        # Ensure the count goes up correctly
        follow_user(user3, user1)

        resp = self.client.get(url_for('users.new_alerts'))
        # Check the JSON response
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.data).get('new_alerts'), 2)

        resp = self.client.get(url_for('users.alerts'))
        # We don't know the alert ID but we can check that one is there by
        # looking for the comment in test mode
        self.assertIn('list:alert:', resp.data)
        self.assertNotIn('Empty', resp.data)
        # Check test2's name is there
        self.assertIn('user2', resp.data)
        # Check that the prettify message from FollowAlert is there
        self.assertIn('has started following you', resp.data)

        # We have now checked the alerts, ensure that i-has-alerts is False
        resp = self.client.get(url_for('users.new_alerts'))
        # Check the JSON response
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.data).get('new_alerts'), 0)

        # Check that we can delete the alert
        # Get the both alert ids from the backend function
        alert1 = get_alerts(user1).items[0].alert_id
        alert2 = get_alerts(user1).items[1].alert_id

        # Check that we don't get a message if there was no alert to delete
        resp = self.client.get(url_for('users.delete_alert',
                                       alert_id=k.NIL_VALUE),
                               follow_redirects=True)
        self.assertNotIn('Alert has been hidden', resp.data)

        # Delete both alerts
        resp = self.client.get(url_for('users.delete_alert', alert_id=alert1),
                               follow_redirects=True)
        self.assertIn('Alert has been hidden', resp.data)
        self.assertNotIn('<!-- list:alert:{} -->'.format(alert1),
                         resp.data)
        self.assertIn('<!-- list:alert:{} -->'.format(alert2),
                      resp.data)

        # Check when the last alert is deleted we get an empty list
        resp = self.client.get(url_for('users.delete_alert', alert_id=alert2),
                               follow_redirects=True)
        self.assertIn('Alert has been hidden', resp.data)
        # Check that there are also no alerts now
        self.assertIn('Empty', resp.data)

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

        self.assertIn('User 2, is here', resp.data)
        self.assertIn('remove:post:{}'.format(post), resp.data)

        # Hide the post
        resp = self.client.post(url_for('users.remove_from_feed',
                                        post_id=post),
                                follow_redirects=True)

        self.assertNotIn('User 2, is here', resp.data)
        self.assertNotIn('remove:post:{}'.format(post), resp.data)
        self.assertIn('Message has been removed from feed', resp.data)

        # Can a user remove their own post?
        post = create_post(user1, 'user1', 'User 1, is here')

        # The user should not see a hide button though
        resp = self.client.get(url_for('users.feed'))
        self.assertIn('User 1, is here', resp.data)
        self.assertNotIn('remove:post:{}'.format(post), resp.data)

        # Ensure the URL hides the post
        resp = self.client.post(url_for('users.remove_from_feed',
                                        post_id=post),
                                follow_redirects=True)

        self.assertNotIn('User 1, is here', resp.data)
        self.assertIn('Message has been removed from feed', resp.data)

        # Ensure removing a post that is not in your feed does not displau a
        # flash message
        resp = self.client.post(url_for('users.remove_from_feed',
                                        post_id=''),
                                follow_redirects=True)

        self.assertNotIn('Message has been removed from feed', resp.data)

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
        self.assertIn('<!-- user:avatar:default -->', resp.data)
        self.assertIn(url_for('static', filename='img/otter_avatar.png'),
                      resp.data)

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
        image = io.BytesIO(open('tests/upload_test_files/otter.jpg').read())

        resp = self.client.post(url_for('users.settings_profile'), data={
            'upload': (image, 'otter.png')
        }, follow_redirects=True)

        user = get_user(user1)

        self.assertIsNotNone(user.get('avatar'))
        self.assertIn('<!-- user:avatar:{} -->'.format(user.get('avatar')),
                      resp.data)

        grid = gridfs.GridFS(m.db, collection='uploads')
        self.assertEqual(grid.find({'filename': user.get('avatar')}).count(),
                         1)

        resp = self.client.get(url_for('posts.get_upload',
                               filename=user.get('avatar')))
        self.assertEqual(resp.status_code, 200)

        # upload another and ensure there is only one in GridFs
        image = io.BytesIO(open('tests/upload_test_files/otter.jpg').read())

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
