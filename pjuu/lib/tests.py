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

# Stdlib imports
from base64 import b64encode
# Pjuu imports
from pjuu.auth.backend import create_user
from pjuu.lib import keys as K
from .alerts import *
from .test_helpers import BackendTestCase


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
        # Use lambda to test the exception comes out.
        # Alerts based on BaseAlert _SHOULD_ implement these themselves
        # With before_alert we will just pass in a fake uid
        self.assertRaises(NotImplementedError, lambda: alert.before_alert(1))
        self.assertRaises(NotImplementedError, lambda: alert.prettify())

        # Create a user an check that at least get_username and get_email work
        self.assertEqual(create_user('test', 'test@pjuu.com', 'Password'), 1)
        alert = BaseAlert(1)
        self.assertEqual(alert.get_username(), 'test')
        self.assertEqual(alert.get_email(), 'test@pjuu.com')
        # Done with BaseAlert :)

    def test_alertmanager(self):
        """
        Test the alert manager.

        Similar to the above a very simple test. Will check that it can alert
        users and one can be created.
        """
        # We need an alert for an AlertManager. Not a problem we will create 2
        self.assertEqual(create_user('test1', 'test1@pjuu.com', 'Password'), 1)
        self.assertEqual(create_user('test2', 'test2@pjuu.com', 'Password'), 2)

        # Check that alert manager will not be created without a valid alert
        # object
        self.assertRaises(TypeError, lambda: AlertManager(1))
        self.assertRaises(TypeError, lambda: AlertManager('1'))

        # Ensure that when an alert manager is created without an alert that
        # we can not use the dumps method
        self.assertRaises(TypeError, lambda: AlertManager().dumps())

        # Ensure that alert is none is we have not passed in alert
        self.assertIsNone(AlertManager().alert)

        # Create an alert so we can test the dumps and the loads methods
        alert = BaseAlert(1)
        am = AlertManager(alert)
        self.assertIsNotNone(am.alert)

        # Dump to a variable so we can load again
        alert_pickle = am.dumps()
        self.assertEqual(type(alert_pickle), str)

        # Check that the alert object and the one stored in the am are the
        # same object
        self.assertIs(alert, am.alert)

        # Check loads
        self.assertTrue(am.loads(alert_pickle))

        # Check the two alerts have the same uid but are not the same object
        self.assertEqual(alert.uid, am.alert.uid)
        self.assertEqual(alert.timestamp, am.alert.timestamp)
        self.assertIsNot(alert, am.alert)
        # Check that the dump is the same from the am as the stored one
        self.assertEqual(alert_pickle, am.dumps())

        # Try an load some stuff that isn't valid
        # A 'Hello world' string :)
        self.assertRaises(TypeError, AlertManager().loads('Hello world'))
        # The same string base64 encoded, this should be a ValueError
        self.assertRaises(ValueError, lambda: AlertManager().loads(
                          b64encode('Hello world')))

        # Test that alerts can be sent to a user.
        # Note: This is more thourogly tested in the users app, as this is
        #       these things are mainly used. Especially pulling out the
        #       from Redis to display them
        # Create an alert
        # test1 will send an alert to test 2
        alert = BaseAlert(1)
        am = AlertManager(alert)
        am.alert_user(2)

        # Check Redis to see if this has gone through.
        # I am just checking this __ONCE__ there are some timing issues with
        # sorted sets and picking the right member, see users.tests for more
        # details
        # Check there is an alert
        self.assertEqual(len(r.zrange(K.USER_ALERTS % 2, 0, -1)), 1)
        # Check the alert loads from Redis
        self.assertTrue(am.loads(r.zrange(K.USER_ALERTS % 2, 0, 0)[0]))
        # Check the alert is the same
        self.assertEqual(am.alert.uid, alert.uid)
        self.assertEqual(am.alert.timestamp, alert.timestamp)
        # Done for now
