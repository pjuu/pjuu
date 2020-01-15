# -*- coding: utf8 -*-

"""Provides stats for the auth package to the dashboard.

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2020 Joe Doherty

"""

from flask import url_for
import pymongo

from pjuu import mongo as m
from pjuu.users.views import timeify_filter
from pjuu.posts.backend import get_post


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

    # Get the 10 highest flagged posts if there is any
    flagged_posts_cur = m.db.posts.find(
        {'flags': {'$gt': 0}}).sort('flags', pymongo.DESCENDING).limit(10)

    flagged_posts = []
    for flagged_post in flagged_posts_cur:
        s = '{0} - <a href="{1}">{2}</a>: <a href="{3}">{4}</a>' + \
            ' [<a href="{5}">Unflag</a>]'

        if flagged_post.get('reply_to') is not None:
            reply_to = get_post(flagged_post.get('reply_to'))
            username = reply_to.get('username')
            post_id = reply_to.get('_id')
        else:
            username = flagged_post.get('username')
            post_id = flagged_post.get('_id')

        link = s.format(
            flagged_post.get('flags'),
            url_for('users.profile',
                    username=flagged_post.get('username')),
            flagged_post.get('username'),
            url_for('posts.view_post',
                    username=username,
                    post_id=post_id),
            flagged_post.get('_id'),
            url_for('posts.unflag_post', post_id=flagged_post.get('_id'))
        )

        # Highligh comments
        if flagged_post.get('reply_to') is not None:
            link = link + ' (comment)'

        flagged_posts.append(link)

    if len(flagged_posts) == 0:
        flagged_posts.append('Empty')

    return [
        ('Total posts', total_posts),
        ('Total uploads', total_uploads),
        ('Last post', last_post_time),
        ('Flagged posts', flagged_posts)
    ]
