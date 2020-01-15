# -*- coding: utf8 -*-

"""Simple tests for auth tokens.

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2020 Joe Doherty

"""

# Pjuu imports
from pjuu import redis as r
from pjuu.lib import keys as k
from pjuu.lib.tokens import check_token, generate_token
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
        r.set(k.TOKEN.format(token1), "{token: 1}")
        self.assertIsNone(check_token(token1))
        # That will have raised our ValueError, I don't know how to trigger a
        # TypeError from Redis as everything is a string

        # Check that preserve on works on tokens
        token1 = generate_token("token1")
        self.assertEqual(check_token(token1, preserve=True), 'token1')
        self.assertEqual(check_token(token1), 'token1')
        self.assertIsNone(check_token(token1))
