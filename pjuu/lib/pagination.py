# -*- coding: utf-8 -*-

"""
Description:
    Provides pagination for Pjuu.

    This does not read anything from Redis it just provides a simple interface
    to handle the issue.

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
from math import ceil


class Pagination(object):
    """Pagination object. Every page which supports the 'page' should
    use this to provide a consistency.

    """

    def __init__(self, items, total, page=1, per_page=50):
        self.items = items
        self.total = total
        self.per_page = per_page
        # Ensure page can not be lower than 1
        if page < 1:
            self.page = 1
        # Ensure page can not be too high.
        # TODO: Fix this
        # This isn't very elagant
        elif page > 4294967295:
            self.page = 4294967295
        else:
            self.page = page

    @property
    def pages(self):
        """Calculate the total number of pages

        """
        if self.per_page == 0:
            pages = 0
        else:
            pages = int(ceil(self.total / float(self.per_page)))
        return pages

    @property
    def has_pages(self):
        return (self.page < self.pages) or (self.page > 1)

    @property
    def prev_page(self):
        if self.page > 1:
            if self.page > self.pages:
                return self.pages
            return self.page - 1
        return None

    @property
    def next_page(self):
        if self.page < self.pages:
            return self.page + 1
        return None


def handle_page(request):
    """Will handle passing 'page' to an view and ensure it is safe

    """
    page = request.args.get('page', None)
    # Ensure the page is a valid integer
    try:
        page = int(page)
        # Catch this twice as this value is also used with Redis to get
        # the relevant ranges from lists and sorted sets
        if page > 4294967295:
            page = 4294967295
        # Pages can't be lower than one
        if page < 1:
            page = 1
    except (TypeError, ValueError):
        # If there was a problem presume the page is 1
        page = 1
    return page
