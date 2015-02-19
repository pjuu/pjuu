# -*- coding: utf8 -*-

"""Provides stats for the auth package to the dashboard.

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2015 Joe Doherty

"""

import pymongo

from pjuu import mongo as m
from pjuu.users.views import timeify_filter


def get_stats():
    """Provides post level statistics.

    """

    total_posts = m.db.posts.count()
    total_uploads = m.db.posts.find(
        {'upload': {'$exists': True}}).count()

    last_post = m.db.posts.find().sort(
        [('created', pymongo.DESCENDING)]).limit(1)
    try:
        last_post_time = timeify_filter(last_post[0].get('created'))
    except IndexError:
        last_post_time = None

    return [
        ('Total posts', total_posts),
        ('Total uploads', total_uploads),
        ('Last post', last_post_time),
    ]
