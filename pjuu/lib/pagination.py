# -*- coding: utf-8 -*-

"""Provides pagination for Pjuu.

This does not read anything from Redis/Mongo it just provides a simple
interface to handle the issue.

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2020 Joe Doherty

"""

# Stdlib imports
from math import ceil


# Max number of pages (don't worry thats a lot of posts/followers)
MAX_PAGES = 4294967295


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
        # Ensure page can not be above a maximum value.
        # Causes issues inside Redis
        elif page > MAX_PAGES:
            self.page = MAX_PAGES
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
    def first_page(self):
        return 1

    @property
    def next_page(self):
        if self.page < self.pages:
            return self.page + 1
        return None

    @property
    def last_page(self):
        return self.pages


def handle_page(request):
    """Will handle passing 'page' to an view and ensure it is safe

    """
    page = request.args.get('page', None)
    # Ensure the page is a valid integer
    try:
        page = int(page)
        # Catch this twice as this value is also used with Redis to get
        # the relevant ranges from lists and sorted sets
        if page > MAX_PAGES:
            page = MAX_PAGES
        # Pages can't be lower than one
        if page < 1:
            page = 1
    except (TypeError, ValueError):
        # If there was a problem presume the page is 1
        page = 1
    return page
