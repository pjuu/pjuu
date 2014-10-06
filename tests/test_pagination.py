# -*- coding: utf8 -*-

"""
Description:
    Pagination tests

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
from pjuu.lib.pagination import *
# Test imports
from tests.helpers import BackendTestCase


class PaginationTests(BackendTestCase):
    """Tests for pagination.

    In Pjuu pagination is a sort of lie. It is an object built up by a
    backend function. It doesn't do a lot

    """

    def test_pagination(self):
        # Create a simple list of numbers to check pagination
        l = [i for i in xrange(1000)]

        p = Pagination(l[:50], len(l), 1, 50)

        # Check basic functionality
        self.assertEqual(p.total, 1000)
        # Read the number of items we have
        self.assertEqual(len(p.items), 50)
        self.assertEqual(p.items, l[:50])
        # The current page we are on
        self.assertEqual(p.page, 1)
        # Per page is how many items to show on each page
        self.assertEqual(p.per_page, 50)
        # Pages is the total number of pages in the entire list
        self.assertEqual(p.pages, 1000 / p.per_page)

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
        p = Pagination(l[:50], len(l), -1, 50)
        self.assertEqual(p.page, 1)

        # Try creating a pagination object with a page larger than
        p = Pagination(l[:50], len(l), 4294967296, 50)
        self.assertEqual(p.page, 4294967295)

        # Done for now
