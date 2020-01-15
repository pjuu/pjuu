# -*- coding: utf8 -*-

"""Pagination tests

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2020 Joe Doherty

"""

# Pjuu imports
from pjuu.lib.pagination import Pagination, handle_page
# Test imports
from tests import BackendTestCase


class PaginationTests(BackendTestCase):
    """Tests for pagination.

    In Pjuu pagination is a sort of lie. It is an object built up by a
    backend function. It doesn't do a lot

    """

    def test_pagination(self):
        # Create a simple list of numbers to check pagination
        ls = [i for i in range(1000)]

        p = Pagination(ls[:50], len(ls), 1, 50)

        # Check basic functionality
        self.assertEqual(p.total, 1000)
        # Read the number of items we have
        self.assertEqual(len(p.items), 50)
        self.assertEqual(p.items, ls[:50])
        # The current page we are on
        self.assertEqual(p.page, 1)
        # Per page is how many items to show on each page
        self.assertEqual(p.per_page, 50)
        # Pages is the total number of pages in the entire list
        self.assertEqual(p.pages, 1000 / p.per_page)

        # Check the pages resolve correct
        self.assertIsNone(p.prev_page)
        self.assertIsNotNone(p.next_page)

        # We are on page 1 ensure prev_page is also 1
        self.assertIsNone(p.prev_page)
        # Ensure the next page is page 2
        self.assertEqual(p.next_page, 2)

        # Set page to the last page
        p.page = p.pages
        self.assertEqual(p.prev_page, p.page - 1)
        self.assertIsNone(p.next_page)

        # Set per_page to 0 and ensure pages is calculated ar 0
        p.per_page = 0
        self.assertEqual(p.pages, 0)

        # Try creating a pagination object with a page lower than 1
        p = Pagination(ls[:50], len(ls), -1, 50)
        self.assertEqual(p.page, 1)

        # Try creating a pagination object with a page larger than
        p = Pagination(ls[:50], len(ls), 4294967296, 50)
        self.assertEqual(p.page, 4294967295)
        self.assertIsNone(p.next_page)
        self.assertIsNotNone(p.prev_page)

        # Ensure last_page shows items / per_page
        p = Pagination(ls[:50], len(ls), 1, 50)
        self.assertEqual(p.last_page, 20)

        p = Pagination(ls[:50], len(ls), 1, 100)
        self.assertEqual(p.last_page, 10)

    def test_handle_page(self):
        """Check the handle_page function, this is important as it stops Redis
        going crazy if the index is too high on a list or sorted set.

        """
        # Create a mock request object so that this functon does not require
        # a request. It gets a request object passed in.
        class Request(object):
            args = {}
        request = Request()

        # Check a couple of values
        self.assertEqual(handle_page(request), 1)
        request.args['page'] = 1000000
        self.assertEqual(handle_page(request), 1000000)
        # Ensure our minimum value can't be broken
        request.args['page'] = -1
        self.assertEqual(handle_page(request), 1)
        # Ensure the maximum value (4294967295) can't be broken
        request.args['page'] = 1000000000000
        self.assertEqual(handle_page(request), 4294967295)

        # Ensure it does not brake with invalid types
        request.args['page'] = None
        self.assertEqual(handle_page(request), 1)
        request.args['page'] = {}
        self.assertEqual(handle_page(request), 1)
