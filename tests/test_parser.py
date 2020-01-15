# -*- coding: utf8 -*-

"""Post backend tests.

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2020 Joe Doherty

"""

from pjuu.auth.backend import create_account, activate
from pjuu.lib.parser import (parse_hashtags, parse_links, parse_mentions,
                             parse_post)

from tests import BackendTestCase


class ParserTests(BackendTestCase):
    """Ensure the text parser, parses correctly."""

    def test_simple_url_http(self):
        """Simple HTTP urls"""
        links = parse_links('Hello http://pjuu.com')
        self.assertEqual(links[0]['link'], 'http://pjuu.com')

    def test_simple_url_https(self):
        """Simpe HTTPS urls"""
        links = parse_links('Hello https://pjuu.com')
        self.assertEqual(links[0]['link'], 'https://pjuu.com')

    def test_urls_are_fixed(self):
        """Ensure simple link are fixed up."""
        links = parse_links('Hello pjuu.com')
        self.assertEqual(links[0]['link'], 'http://pjuu.com')
        self.assertEqual(links[0]['span'], (6, 14))

    def test_anchors_in_urls(self):
        """Query strings and anchor points"""
        links = parse_links('https://pjuu.com/joe?page=2#hello')
        self.assertEqual(links[0]['link'], 'https://pjuu.com/joe?page=2#hello')

    def test_weird_query_strings(self):
        """Ensure strange characters are handled"""
        links = parse_links(
            'http://pjuu.com:5000/a/post/url?page=1&q=abc,def#something')
        self.assertEqual(
            links[0]['link'],
            'http://pjuu.com:5000/a/post/url?page=1&q=abc,def#something')

    def test_hashtags_are_not_parsed(self):
        """Ensure achors are not parsed as hashtags"""
        hashtags = parse_hashtags(
            'http://pjuu.com:5000/a/post/url?page=1&q=abc,def#something')
        self.assertEqual(len(hashtags), 0)

    def test_urls_and_hashtags(self):
        """Hashtags intermixed with urls"""
        links, mentions, hashtags = parse_post('pjuu.com/#bottom #plop')
        self.assertEqual(links[0]['link'], 'http://pjuu.com/#bottom')
        self.assertEqual(hashtags[0]['hashtag'], 'plop')

    def test_short_hashtags(self):
        """Hashtags musy be more than 1 character long."""
        hashtags = parse_hashtags('#cheese #j #jo #joe')
        self.assertEqual(hashtags[0]['hashtag'], 'cheese')
        self.assertEqual(hashtags[1]['hashtag'], 'jo')
        self.assertEqual(hashtags[2]['hashtag'], 'joe')

    def test_mention_no_user(self):
        """Find a user mention (doens't exist)"""
        mentions = parse_mentions('@joe @ant', check_user=False)
        self.assertEqual(mentions[0]['username'], 'joe')
        self.assertEqual(mentions[0]['user_id'], 'NA')
        self.assertEqual(mentions[0]['span'], (0, 4))
        self.assertEqual(mentions[1]['username'], 'ant')
        self.assertEqual(mentions[1]['user_id'], 'NA')
        self.assertEqual(mentions[1]['span'], (5, 9))

    def test_mention_real_user(self):
        """Find a user mentions (user does exist)"""
        user1 = create_account('user1', 'user1@pjuu.com', 'Password1')
        activate(user1)
        mentions = parse_mentions('@user1 @user2')
        self.assertEqual(len(mentions), 1)
        self.assertEqual(mentions[0]['username'], 'user1')
        self.assertEqual(mentions[0]['user_id'], user1)
        self.assertEqual(mentions[0]['span'], (0, 6))

    def test_unicode_character(self):
        """Do unicode characters break things."""
        user1 = create_account('user1', 'user1@pjuu.com', 'Password1')
        activate(user1)
        links, mentions, hashtags = parse_post('၍ @user1, ☂pjuu.com, 㒅 #hash')
        self.assertEqual(links[0]['link'], 'http://pjuu.com')
        self.assertEqual(mentions[0]['username'], 'user1')
        self.assertEqual(hashtags[0]['hashtag'], 'hash')

    def test_surrounding_characters(self):
        """Can parse objects be in parenthesis"""
        user1 = create_account('user1', 'user1@pjuu.com', 'Password1')
        activate(user1)
        links, mentions, hashtags = parse_post('(@user1), (pjuu.com), (#hash)')
        self.assertEqual(links[0]['link'], 'http://pjuu.com')
        self.assertEqual(mentions[0]['username'], 'user1')
        self.assertEqual(hashtags[0]['hashtag'], 'hash')

    def test_parenethesis_in_paths(self):
        """Handle URLs surrounded by parenthesis and containing them."""
        links = parse_links('(https://pjuu.com/user1)')
        self.assertEqual(links[0]['link'], 'https://pjuu.com/user1')
        links = parse_links('https://pjuu.com/user1(awesome)')
        self.assertEqual(links[0]['link'], 'https://pjuu.com/user1(awesome)')

    def test_quoting_mentions_hashtags(self):
        """Parenthesis around items"""
        links = parse_links('"https://pjuu.com/user1"')
        self.assertEqual(links[0]['link'], 'https://pjuu.com/user1')
        hashtags = parse_hashtags('"#pjuu"')
        self.assertEqual(hashtags[0]['hashtag'], 'pjuu')
        mentions = parse_mentions('"@joe"', check_user=False)
        self.assertEqual(mentions[0]['username'], 'joe')

    def test_delimited(self):
        """Ensure hashtags can be delimited"""
        hashtags = parse_hashtags('#pjuu\'s test')
        self.assertEqual(hashtags[0]['hashtag'], 'pjuu')

        user1 = create_account('user1', 'user1@pjuu.com', 'Password1')
        activate(user1)
        mentions = parse_mentions('@user1\'s')
        self.assertEqual(mentions[0]['username'], 'user1')
        self.assertEqual(mentions[0]['user_id'], user1)
