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
from pjuu.lib import keys as K
from pjuu.lib.tokens import *
# Test imports
from tests import BackendTestCase


class TokenTests(BackendTestCase):
    """Test everything about tokens. (there is not a lot :P)

    """

    def test_tokens(self):
        """Generate and check a few tokens, simple.

        """
        # Test normal token operations
        token1 = generate_token("token1")
        self.assertEqual(check_token(token1), "token1")
        # Check that getting the token again returns nothing
        self.assertIsNone(check_token(token1))

        # Create another token just this time check it initially with preserve
        token1 = generate_token("token1")
        self.assertEqual(check_token(token1, preserve=True), "token1")
        # Get it again with no preserve and check we get the correct answer
        self.assertEqual(check_token(token1), "token1")

        # Try creating a token with some Python objects
        token1 = generate_token({"name": "token1"})
        self.assertEqual(check_token(token1).get("name"), "token1")

        # A token with None stored would not work as the same outcome would
        # happen as if there was not a token
        token1 = generate_token(None)
        # POINTLESS!
        self.assertIsNone(check_token(token1))

        # Try and break check tokens
        # Check a token that I just made up, not a hex UUID
        self.assertIsNone(check_token("token1"))

        # Create a token and mangle the data inside Redis
        token1 = generate_token("token1")
        # Not a valid JSON pickle, the dict is invalid
        r.set(K.TOKEN.format(token1), "{token: 1}")
        self.assertIsNone(check_token(token1))
        # That will have raised our ValueError, I don't know how to trigger a
        # TypeError from Redis as everything is a string

        # Check that preserve on works on tokens
        token1 = generate_token("token1")
        self.assertEqual(check_token(token1, preserve=True), 'token1')
        self.assertEqual(check_token(token1), 'token1')
        self.assertIsNone(check_token(token1))
