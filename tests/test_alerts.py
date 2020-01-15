# -*- coding: utf8 -*-

"""Basic tests for the base alert system. These should also be tested in each
backend test for the specific alerts that appear there.

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2020 Joe Doherty

"""

# Pjuu imports
from pjuu import redis as r
from pjuu.auth.backend import create_account, delete_account
from pjuu.lib import keys as k
from pjuu.lib.alerts import AlertManager, BaseAlert
# Test imports
from tests import BackendTestCase


class AlertTests(BackendTestCase):

    def test_basealert(self):
        """Simple test for alerts.

        Ensure that they do what we want them too do out of the box.

        Ensure user() works. Also check that the AlertManager can't be broken.

        """
        # Check that an alert will not work with a non-existant get_user
        alert = BaseAlert(k.NIL_VALUE)
        # Check that there is a timestamp
        self.assertGreater(alert.timestamp, 0)
        # We should get nothing back for alerts when it comes to our
        # existant user
        self.assertIsNone(alert.user)
        # Check that the alert does NOT verify
        self.assertFalse(alert.verify())
        # Use lambda to test the exception comes out.
        # Alerts based on BaseAlert _SHOULD_ implement these themselves
        self.assertRaises(NotImplementedError, lambda: alert.prettify())

        # Create a user an check that at least get_username and get_email work
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        alert = BaseAlert(user1)
        self.assertEqual(alert.user.get('username'), 'user1')
        self.assertEqual(alert.user.get('email'), 'user1@pjuu.com')
        self.assertTrue(alert.verify())
        # Done with BaseAlert :)

    def test_alertmanager(self):
        """
        Test the alert manager.

        Similar to the above a very simple test. Will check that it can alert
        users and one can be created.
        """
        # Create our alert manager
        am = AlertManager()

        # Try and load a non-existant alert
        self.assertIsNone(am.get(k.NIL_VALUE))

        # Try and alert on something which is not an alert
        self.assertRaises(ValueError, lambda: am.alert('ALERT', k.NIL_VALUE))

        # Test that alerting a single users does not work, they need to be
        # iterable
        # Create an alert
        alert = BaseAlert(k.NIL_VALUE)
        self.assertRaises(TypeError, lambda: am.alert(alert, 1))

        # Create a couple of users
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        user2 = create_account('user2', 'user2@pjuu.com', 'Password')

        # Ensure the length of user1's alert feed is 0
        self.assertEqual(r.zcard(k.USER_ALERTS.format(user1)), 0)

        # Create an alert from user2
        alert = BaseAlert(user2)
        # Alert user1
        am.alert(alert, [user1])

        # Ensure the length of user1's alert feed is 1
        self.assertEqual(r.zcard(k.USER_ALERTS.format(user1)), 1)

        # Get alerts for user1, user Redis directly
        alerts = r.zrange(k.USER_ALERTS.format(user1), 0, 0)
        # Get the alert from alerts
        alert = am.get(alerts[0])
        self.assertIsNotNone(alert)
        self.assertEqual(alert.user.get('username'), 'user2')
        self.assertEqual(alert.user.get('email'), 'user2@pjuu.com')

        # Delete test2 and ensure getting the alert returns None
        delete_account(user2)
        alert = am.get(alerts[0])
        self.assertIsNone(alert)

        # Done for now, may need expanding for coverage
