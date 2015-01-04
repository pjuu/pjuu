# -*- coding: utf8 -*-

"""We have moved on main database away from Redis and to MongoDB.

I won't discuss the politics here but we can't afford to keep all our
users, posts and comments data inside Redis if the site ever got big. We
chose MongoDB so we didn't have to change the way we work. This also makes
it easier for others to trust that this data is safe. Redis can be tricky
to do correctly.

:license: AGPL v3, see LICENSE for more details
:copyright: 2014 Joe Doherty

"""
