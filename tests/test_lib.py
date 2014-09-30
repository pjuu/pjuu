# -*- coding: utf8 -*-

"""
Description:
    Tests for library modules.

    Note: Each module should be split in to it's own test case!
    Note: Most of these tests should extend BackendTestCase, nothing in the lib
          module should ever need testing from a front end point of view

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

# Pjuu imports
from pjuu.auth.backend import create_user, delete_account
from pjuu.lib import keys as K
from pjuu.lib.alerts import *
# Test imports
from tests.helpers import BackendTestCase


class AlertTests(BackendTestCase):

    def test_basealert(self):
        """
        Simple test for alerts.

        Ensure that they do what we want them too do out of the box.

        Ensure get_username and get_email work. Also check that the
        AlertManager can't be broken.
        """
        # Check that an alert will not work with a non-existant get_user
        alert = BaseAlert(1000)
        # Check that there is a timestamp
        self.assertGreater(alert.timestamp, 0)
        # We should get nothing back for alerts when it comes to our
        # existant user
        self.assertIsNone(alert.get_username())
        self.assertIsNone(alert.get_email())
        # Check that the alert does NOT verify
        self.assertFalse(alert.verify())
        # Use lambda to test the exception comes out.
        # Alerts based on BaseAlert _SHOULD_ implement these themselves
        self.assertRaises(NotImplementedError, lambda: alert.prettify())

        # Create a user an check that at least get_username and get_email work
        user = create_user('test', 'test@pjuu.com', 'Password')
        alert = BaseAlert(user)
        self.assertEqual(alert.get_username(), 'test')
        self.assertEqual(alert.get_email(), 'test@pjuu.com')
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
        self.assertIsNone(am.get(123))

        # Try and alert on something which is not an alert
        self.assertRaises(ValueError, lambda: am.alert('ALERT', [1, 2, 3]))

        # Test that alerting a single users does not work, they need to be
        # iterable
        # Create an alert
        alert = BaseAlert(1)
        self.assertRaises(TypeError, lambda: am.alert(alert, 1))

        # Create a couple of users
        user1 = create_user('test1', 'test1@pjuu.com', 'Password')
        user2 = create_user('test2', 'test2@pjuu.com', 'Password')

        # Ensure the length of user1's alert feed is 0
        self.assertEqual(r.zcard(K.USER_ALERTS % user1), 0)

        # Create an alert from user2
        alert = BaseAlert(user2)
        # Alert user1
        am.alert(alert, [user1])

        # Ensure the length of user1's alert feed is 1
        self.assertEqual(r.zcard(K.USER_ALERTS % user1), 1)

        # Get alerts for user1, user Redis directly
        alerts = r.zrange(K.USER_ALERTS % user1, 0, 0)
        # Get the alert from alerts
        alert = am.get(alerts[0])
        self.assertIsNotNone(alert)
        self.assertEqual(alert.get_username(), 'test2')
        self.assertEqual(alert.get_email(), 'test2@pjuu.com')

        # Delete test2 and ensure getting the alert returns None
        delete_account(user2)
        alert = am.get(alerts[0])
        self.assertIsNone(alert)

        # Done for now, may need expanding for coverage
