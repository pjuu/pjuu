# -*- coding: utf-8 -*-
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


def handle_page(request, default_url='/'):
    """
    Will handle passing 'page' to an view and ensure it is safe
    """
    page = request.values.get('page', None)
    # Ensure the page is a valid integer
    try:
        page = int(page)
    except (TypeError, ValueError):
        page = 1
    return page
