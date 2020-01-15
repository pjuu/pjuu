# -*- coding: utf8 -*-

"""Users backend tests.

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2020 Joe Doherty

"""

from flask import current_app as app

from pjuu import mongo as m, redis as r
from pjuu.auth.backend import create_account, delete_account, activate
from pjuu.lib import keys as k
from pjuu.lib.alerts import BaseAlert
from pjuu.posts.backend import create_post
from pjuu.users.backend import (
    get_profile, search, is_following, get_following, get_followers,
    new_alerts, FollowAlert, get_alerts, follow_user, unfollow_user,
    delete_alert, get_user, approve_user, unapprove_user, is_trusted,
    get_trusted
)
from pjuu.auth.utils import get_uid_username

from tests import BackendTestCase


class BackendTests(BackendTestCase):
    """
    This case will test ALL post backend functions.
    """

    def test_get_profile(self):
        """
        Tests that a user's profile representation can be returned
        """
        # Get test user
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        # Attempt to get the users repr
        profile = get_profile(user1)
        # Ensure we got a profile
        self.assertIsNotNone(profile)

        # Check all the keys are present
        self.assertEqual(profile.get('_id'), user1)
        self.assertEqual(profile.get('username'), 'user1')
        self.assertEqual(profile.get('email'), 'user1@pjuu.com')
        # Ensure all the injected information is present
        self.assertEqual(profile.get('post_count'), 0)
        self.assertEqual(profile.get('followers_count'), 0)
        self.assertEqual(profile.get('following_count'), 0)

        # Ensure a non-existant profile return None
        self.assertEqual(get_profile(k.NIL_VALUE), None)

    def test_get_user(self):
        """
        Tests that a user's account can be returned
        """
        # Get test user
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        # Attempt to get the users repr
        user = get_user(user1)
        # Ensure we got a profile
        self.assertIsNotNone(user)
        # Check all the keys are present
        self.assertEqual(user.get('_id'), user1)
        self.assertEqual(user.get('username'), 'user1')
        self.assertEqual(user.get('email'), 'user1@pjuu.com')
        # Ensure a non-existant user return None
        self.assertEqual(get_user(k.NIL_VALUE), None)

    def test_follow_unfollow_get_followers_following_is_following(self):
        """
        Test everything about following. There is not that much to it to
        deserve 3 seperate methods.
        """
        # Create two test users
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        user2 = create_account('user2', 'user2@pjuu.com', 'Password')
        # Ensure is_following() is false atm
        self.assertFalse(is_following(user1, user2))
        self.assertFalse(is_following(user2, user1))
        # Ensure user 1 can follow user 2
        self.assertTrue(follow_user(user1, user2))
        # Ensure the user can't follow them again
        self.assertFalse(follow_user(user1, user2))
        # And visa-versa
        self.assertTrue(follow_user(user2, user1))
        # Ensre the user can't follow them again
        self.assertFalse(follow_user(user2, user1))
        # Ensure the id's are in the Redis sorted sets, followers and following
        self.assertIn(user2, r.zrange(k.USER_FOLLOWING.format(user1), 0, -1))
        self.assertIn(user2, r.zrange(k.USER_FOLLOWERS.format(user1), 0, -1))
        self.assertIn(user1, r.zrange(k.USER_FOLLOWING.format(user2), 0, -1))
        self.assertIn(user1, r.zrange(k.USER_FOLLOWERS.format(user2), 0, -1))
        # Ensure the get_followers and get_following functions return
        # the correct data
        self.assertEqual(len(get_following(user1).items), 1)
        self.assertEqual(len(get_following(user1).items), 1)
        self.assertEqual(len(get_following(user2).items), 1)
        self.assertEqual(len(get_following(user2).items), 1)
        # Ensure the totals are correct
        self.assertEqual(get_following(user1).total, 1)
        self.assertEqual(get_followers(user1).total, 1)
        self.assertEqual(get_following(user2).total, 1)
        self.assertEqual(get_followers(user2).total, 1)

        # Make sure is_following() returns correctly
        self.assertTrue(is_following(user1, user2))
        self.assertTrue(is_following(user2, user1))

        # User 1 unfollow user 2 and ensure the sorted sets are updated
        self.assertTrue(unfollow_user(user1, user2))
        self.assertNotIn(user2,
                         r.zrange(k.USER_FOLLOWING.format(user1), 0, -1))
        self.assertNotIn(user1,
                         r.zrange(k.USER_FOLLOWERS.format(user2), 0, -1))

        # Ensure the user can't unfollow the user again
        self.assertFalse(unfollow_user(user1, user2))
        # Ensure is_following shows correctly
        self.assertFalse(is_following(user1, user2))

        # Test what happens when we delete an account.

        # Ensure user 2 is still following user1
        self.assertTrue(is_following(user2, user1))

        # This should clean
        delete_account(user1)

        # Ensure this has cleaned user2 following list
        self.assertFalse(is_following(user2, user1))

        # Ensure get_followers and get_following return the correct value for
        # user2
        self.assertEqual(len(get_following(user2).items), 0)
        # Ensure the totals are correct
        self.assertEqual(get_following(user2).total, 0)
        self.assertEqual(get_followers(user2).total, 0)
        # Make sure is_following() returns correctly
        self.assertFalse(is_following(user1, user2))
        self.assertFalse(is_following(user2, user1))

        # I don't want to play with the above testing to much. I am adding
        # in a test for self cleaning lists. I am going to reset this test
        # case by manually flushing the Redis database :)
        r.flushdb()
        # Back to normal, I don't like artificially uping the number of tests.

        # Test the self cleaning lists in case there is an issue with Redis
        # during an account deletion. We need 2 new users.
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        user2 = create_account('user2', 'user2@pjuu.com', 'Password')

        # Follow each other.
        self.assertTrue(follow_user(user1, user2))
        self.assertTrue(follow_user(user2, user1))

        # Manually delete user1
        m.db.users.remove({'_id': user1})

        # Ensure user1 appears in both user2's followers and following lists
        self.assertIn(user1, r.zrange(k.USER_FOLLOWERS.format(user2), 0, -1))
        self.assertIn(user1, r.zrange(k.USER_FOLLOWING.format(user2), 0, -1))

        # Ensure if we actuallt get the lists from the backend functions user1
        # is not there
        self.assertEqual(get_followers(user2).total, 0)
        self.assertEqual(get_following(user2).total, 0)

    def test_approved_unapproved_is_trusted(self):
        """Ensure a user can trust and un-trust a follower. Also test the
        checking of this state
        """
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        user2 = create_account('user2', 'user2@pjuu.com', 'Password')
        user3 = create_account('user3', 'user3@pjuu.com', 'Password')

        # User should not be following a user
        self.assertFalse(is_trusted(user1, user2))

        # User can't approve a user he is not following
        self.assertFalse(approve_user(user1, user2))

        # Follow wrong way round. The user to be trusted must follow you
        follow_user(user1, user2)
        self.assertFalse(approve_user(user1, user2))
        self.assertFalse(is_trusted(user1, user2))

        # Correct way round
        follow_user(user2, user1)
        self.assertTrue(approve_user(user1, user2))
        self.assertTrue(is_trusted(user1, user2))

        # Try an un-approved a non follower
        self.assertFalse(is_trusted(user1, user3))
        self.assertFalse(unapprove_user(user1, user3))

        # Try and un-approve a non approved follower
        follow_user(user3, user1)
        self.assertFalse(is_trusted(user1, user3))
        self.assertFalse(unapprove_user(user1, user3))

        # Un-approve an approved folloer
        self.assertTrue(is_trusted(user1, user2))
        self.assertTrue(unapprove_user(user1, user2))
        self.assertFalse(is_trusted(user1, user2))

        # Ensure a user is un-approved if they stop following you
        # and you had approved them
        self.assertTrue(approve_user(user1, user2))
        self.assertTrue(is_trusted(user1, user2))
        unfollow_user(user2, user1)
        self.assertFalse(is_trusted(user1, user2))

    def test_followers_and_unfollowers_pagination_sizes(self):
        """Ensure that the followers and unfollowers feeds are correct if
        changing the feed size.
        """
        users = []
        # Creae 101 users (0 - 100)
        for i in range(101):
            users.append(create_account('user{}'.format(i),
                                        'user{}@pjuu.com'.format(i),
                                        'Password'))

        # Make user0 follow all users and visa versa
        for i in range(1, 101):
            follow_user(users[0], users[i])
            follow_user(users[i], users[0])

        FEED_ITEMS_PER_PAGE = app.config.get('FEED_ITEMS_PER_PAGE')

        # Check that the correct amount of users come back for follower and
        # following
        self.assertEqual(len(get_followers(users[0]).items),
                         FEED_ITEMS_PER_PAGE)

        self.assertEqual(len(get_followers(users[0], per_page=25).items), 25)
        self.assertEqual(len(get_followers(users[0], per_page=50).items), 50)
        self.assertEqual(len(get_followers(users[0], per_page=100).items), 100)

        self.assertEqual(len(get_following(users[0]).items),
                         FEED_ITEMS_PER_PAGE)

        self.assertEqual(len(get_following(users[0], per_page=25).items), 25)
        self.assertEqual(len(get_following(users[0], per_page=50).items), 50)
        self.assertEqual(len(get_following(users[0], per_page=100).items), 100)

    def test_back_feed(self):
        """Test the back feed feature, once a user follows another user it
        places their latest 5 posts on their feed. They will be in chronologic
        order.

        I know that ``back_feed()`` is a posts feature but it is triggered on
        follow.

        """
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        user2 = create_account('user2', 'user2@pjuu.com', 'Password')

        # Create 6 test posts ('Test 1' shouldn't be back fed)
        post1 = create_post(user1, 'user1', 'Test 1')
        post2 = create_post(user1, 'user1', 'Test 2')
        post3 = create_post(user1, 'user1', 'Test 3')
        post4 = create_post(user1, 'user1', 'Test 4')
        post5 = create_post(user1, 'user1', 'Test 5')
        post6 = create_post(user1, 'user1', 'Test 6')

        follow_user(user2, user1)

        # Check that the posts are in the feed (we can do this in Redis)
        feed = r.zrevrange(k.USER_FEED.format(user2), 0, -1)

        self.assertNotIn(post1, feed)
        self.assertIn(post2, feed)
        self.assertIn(post3, feed)
        self.assertIn(post4, feed)
        self.assertIn(post5, feed)
        self.assertIn(post6, feed)

    def test_search(self):
        """Make sure users can actually find things on the site."""
        # Create test user
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        # Ensure that the user can be found
        self.assertEqual(len(search('user1').items), 0)
        self.assertEqual(search('user1').total, 0)

        # Users will not appear unless they are active.
        activate(user1)
        self.assertEqual(len(search('user1').items), 1)
        self.assertEqual(search('user1').total, 1)

        # Ensure partial match
        self.assertEqual(len(search('use').items), 1)
        self.assertEqual(search('use').total, 1)
        # Ensure nothing return if no user
        self.assertEqual(len(search('user2').items), 0)
        self.assertEqual(search('user2').total, 0)
        # Ensure no partial if incorrect
        self.assertEqual(len(search('bob').items), 0)
        self.assertEqual(search('bob').total, 0)

        # Create a second test user and a post with a hashtag and
        # ensure both show in the results.
        user2 = create_account('user2', 'user2@pjuu.com', 'Password')
        activate(user2)
        # Create the post as user1 as we are going to delete user2
        create_post(user1, 'user1', '#user2')
        # Ensure the new user can be found
        self.assertEqual(len(search('user2').items), 2)
        self.assertEqual(search('user2').total, 2)
        # Ensure partial match returns both test1/2 users
        self.assertEqual(len(search('use').items), 3)
        self.assertEqual(search('use').total, 3)

        # Delete the account user2 and try searching again
        # Only the hashtag should show
        delete_account(user2)
        self.assertEqual(search('user2').total, 1)
        # Done

    def test_advanced_search(self):
        """Cover using the `@` and `#` modifiers to limit the search type."""
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        user2 = create_account('user2', 'user2@pjuu.com', 'Password')

        # We have to activate the accounts to appear in the search
        activate(user1)
        activate(user2)

        create_post(user1, 'user1', '#pjuu #user2')
        create_post(user2, 'user2', '#pjuu #user1')

        for i in range(1, 101):
            create_post(user1, 'user1', '#pagination{}'.format(i))

        # No user should appear because they are not active!
        self.assertEqual(search('user').total, 4)
        self.assertEqual(search('user1').total, 2)
        self.assertEqual(search('user2').total, 2)

        # Try come basic search terms
        self.assertEqual(search('user').total, 4)
        self.assertEqual(search('user1').total, 2)
        self.assertEqual(search('user2').total, 2)
        self.assertEqual(search('pjuu').total, 2)

        # Users only
        self.assertEqual(search('@user').total, 2)
        self.assertEqual(search('@user1').total, 1)
        # erroneous spacing doesn't matter
        self.assertEqual(search('@    us').total, 2)

        # Posts only
        self.assertEqual(search('#user').total, 2)
        self.assertEqual(search('#user1').total, 1)
        self.assertEqual(search('#pjuu').total, 2)

        # Test pagination in search
        self.assertEqual(len(search('#pagination', 1, 50).items), 50)
        self.assertEqual(len(search('#pagination', 2, 50).items), 50)

    def test_alerts(self):
        """
        Tests for the 2 functions which are used on the side to get alerts and
        also test FollowAlert from here.
        """
        # Create 2 test users
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        user2 = create_account('user2', 'user2@pjuu.com', 'Password')

        # Ensure that get_alerts pagination object is empty
        self.assertEqual(get_alerts(user1).total, 0)
        self.assertEqual(len(get_alerts(user1).items), 0)

        # Get user 2 to follow user 1
        follow_user(user2, user1)

        # Check that i_has_alerts is True
        self.assertTrue(new_alerts(user1))

        # Ensure that there is an alert in the get_alerts
        self.assertEqual(get_alerts(user1).total, 1)
        self.assertEqual(len(get_alerts(user1).items), 1)

        # Check that i_has_alerts is False, we have read them with get_alerts
        self.assertFalse(new_alerts(user1))

        # Get the alert and check that the alert is the follow alert
        alert = get_alerts(user1).items[0]
        self.assertTrue(isinstance(alert, FollowAlert))
        # Also check it's still a BaseAlert
        self.assertTrue(isinstance(alert, BaseAlert))
        # Check its from test2
        self.assertEqual(alert.user.get('username'), 'user2')
        self.assertEqual(alert.user.get('email'), 'user2@pjuu.com')
        self.assertIn('has started following you', alert.prettify())

        # Delete test2 and ensure we get no alerts
        delete_account(user2)

        # Ensure the alert is still inside Redis
        self.assertEqual(r.zcard(k.USER_ALERTS.format(user1)), 1)

        # Get the alerts, should be none and should also clear the alert from
        # Redis
        self.assertEqual(get_alerts(user1).total, 0)
        self.assertEqual(len(get_alerts(user1).items), 0)
        self.assertEqual(r.zcard(k.USER_ALERTS.format(user1)), 0)

        # Do the same as above to ensure we can delete an alert ourselves
        # Create another user
        user3 = create_account('user3', 'user3@pjuu.com', 'Password')

        follow_user(user1, user3)

        # Check the alerts are there
        alert = get_alerts(user3).items[0]
        self.assertTrue(isinstance(alert, FollowAlert))
        # Also check it's still a BaseAlert
        self.assertTrue(isinstance(alert, BaseAlert))
        # Check its from test2
        self.assertEqual(alert.user.get('username'), 'user1')
        self.assertEqual(alert.user.get('email'), 'user1@pjuu.com')
        self.assertIn('has started following you', alert.prettify())

        # Delete the alert with aid from the alert
        delete_alert(user3, alert.alert_id)

        # Get the alerts and ensure the list is empty
        self.assertEqual(get_alerts(user3).total, 0)
        self.assertEqual(len(get_alerts(user3).items), 0)
        self.assertEqual(r.zcard(k.USER_ALERTS.format(user3)), 0)

        # Unfollow the user3 and then follow them again
        unfollow_user(user1, user3)
        follow_user(user1, user3)

        alert = get_alerts(user3).items[0]
        self.assertIn('has started following you', alert.prettify())

        # Manually delete the alert
        r.delete(k.ALERT.format(alert.alert_id))

        # Get the alerts again and ensure the length is 0
        # Ensure that the alert is not pulled down
        alerts = get_alerts(user3)
        self.assertEqual(len(alerts.items), 0)

        # Get alerts for a non-existant user
        # This will not fail but will have an empty pagination
        alerts = get_alerts(k.NIL_VALUE)
        self.assertEqual(len(alerts.items), 0)

        # Done for now

    def test_alerts_pagination_sizes(self):
        """Check that the correct number of alerts are generated"""
        # Create 2 test users
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        user2 = create_account('user2', 'user2@pjuu.com', 'Password')

        # Generate lots of following alerts
        for i in range(101):
            follow_user(user2, user1)
            unfollow_user(user2, user1)

        ALERT_ITEMS_PER_PAGE = app.config.get('ALERT_ITEMS_PER_PAGE')

        self.assertEqual(len(get_alerts(user1).items), ALERT_ITEMS_PER_PAGE)
        self.assertEqual(len(get_alerts(user1, per_page=25).items), 25)
        self.assertEqual(len(get_alerts(user1, per_page=50).items), 50)
        self.assertEqual(len(get_alerts(user1, per_page=100).items), 100)

    def test_get_trusted(self):
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        activate(user1)

        # Create loads of users have the follow user1 and have them trusted
        for i in range(2, 102):
            user = create_account('user{}'.format(i),
                                  'user{}@pjuu.com'.format(i),
                                  'password')
            activate(user)
            follow_user(user, user1)
            approve_user(user1, user)

        self.assertEqual(get_trusted(user1).total, 100)

        for i in range(2, 102, 2):
            delete_account(get_uid_username('user{}'.format(i)))

        self.assertEqual(get_trusted(user1).total, 50)

        # Test per page
        trusted_pagination = get_trusted(user1, per_page=10)
        self.assertEqual(trusted_pagination.total, 50)
        # The answer is 5 because of the self cleaning action
        self.assertEqual(len(trusted_pagination.items), 5)
