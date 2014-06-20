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
    """
    Pagination object. Every page which supports the 'page' should
    use this to provide a consistency.
    """

    def __init__(self, items, total, page=1, per_page=50):
        self.items = items
        self.total = total
        self.page = page
        self.per_page = per_page

    @property
    def pages(self):
        """
        The total number of pages
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
    def prev_num(self):
        return self.page - 1

    @property
    def has_prev(self):
        return self.page > 1

    @property
    def next_num(self):
        return self.page + 1

    @property
    def has_next(self):
        return self.page < self.pages


def handle_page(request):
    """
    Will handle passing 'page' to an view and ensure it is safe
    """
    page = request.args.get('page', None)
    # Ensure the page is a valid integer
    try:
        page = int(page)
    except (TypeError, ValueError):
        page = 1
    return page
