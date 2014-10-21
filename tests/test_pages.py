# -*- coding: utf8 -*-

"""
Description:
    Tests the simple page module for displaying non-dynamic pages

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
from flask import url_for
# Pjuu imports
from pjuu.auth.backend import create_user, activate
# Test imports
from tests import FrontendTestCase


class PagesTests(FrontendTestCase):
    """Test that the pages are rendered

    """

    def test_logged_out(self):
        """Check the pages work when logged test_logged_out

        """
        # Abouts
        resp = self.client.get(url_for('about'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('<!-- menu: not logged in -->', resp.data)
        self.assertIn('<h1>About Us</h1>', resp.data)

        # Terms
        resp = self.client.get(url_for('terms'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('<!-- menu: not logged in -->', resp.data)
        self.assertIn('<h1>Terms of Service</h1>', resp.data)

        # Privacy
        resp = self.client.get(url_for('privacy'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('<!-- menu: not logged in -->', resp.data)
        self.assertIn('<h1>Privacy Policy</h1>', resp.data)

    def test_logged_in(self):
        """Check the pages work when logged in

        """
        # Let's create a user an login
        user1 = create_user('user1', 'user1@pjuu.com', 'Password')
        # Activate the account
        self.assertTrue(activate(user1))
        # Log the user in
        resp = self.client.post(url_for('signin'), data={
            'username': 'user1',
            'password': 'Password'
        }, follow_redirects=True)

        # About
        resp = self.client.get(url_for('about'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('<!-- menu: logged in -->', resp.data)
        self.assertIn('<h1>About Us</h1>', resp.data)

        # Terms
        resp = self.client.get(url_for('terms'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('<!-- menu: logged in -->', resp.data)
        self.assertIn('<h1>Terms of Service</h1>', resp.data)

        # Privacy
        resp = self.client.get(url_for('privacy'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('<!-- menu: logged in -->', resp.data)
        self.assertIn('<h1>Privacy Policy</h1>', resp.data)
