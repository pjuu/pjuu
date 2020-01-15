# -*- coding: utf8 -*-

"""Provides stats for the auth package to the dashboard.

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2020 Joe Doherty

"""

from flask import url_for
import pymongo

from pjuu import mongo as m


def get_stats():
    """Provides authentication stats on users.

    """

    total_users = m.db.users.count()
    total_active = m.db.users.find({'active': True}).count()
    total_banned = m.db.users.find({'banned': True}).count()
    total_muted = m.db.users.find({'muted': True}).count()
    total_op = m.db.users.find({'op': True}).count()

    newest_users_cur = m.db.users.find(
        {}, {'_id': False, 'username': True, 'active': True}
    ).sort(
        [('created', pymongo.DESCENDING)]
    ).limit(10)
    newest_users = []
    for user in newest_users_cur:
        # If the user is active show a green circle else red
        if user.get('active'):
            active_string = 'green'
        else:
            active_string = 'red'

        link = '<a href="{0}"><i class="fa fa-circle {1}"></i> {2}</a>'.format(
            url_for('users.profile', username=user.get('username')),
            active_string,
            user.get('username')
        )
        newest_users.append(link)

    return [
        ('Total users', total_users),
        ('Total active users', total_active),
        ('Total banned users', total_banned),
        ('Total muted users', total_muted),
        ('Total OP users', total_op),
        ('Newest users', newest_users),
    ]
