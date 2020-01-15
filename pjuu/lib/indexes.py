# -*- coding: utf8 -*-

"""Creates the MongoDB indexes. This can be run each time the app is deployed
it will have no effect on indexes which are already there.

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2020 Joe Doherty

"""

# 3rd party imports
import pymongo
# Pjuu imports
from pjuu import mongo as m
from pjuu.lib import keys as k


def ensure_indexes():
    """Creates all our MongoDB indexes.

    Please note that _id fields are already indexed by MongoDB. If you need to
    lookup a document by a field that is not in here, ensure you need it! If
    it is a one off like how many users are banned it doesn't need to be here.
    If you look up by a key all the time (new feature) it will probably need to
    be indexed.

    """
    # User indexes
    # User name and e-mail address have to be unique across the database
    m.db.users.ensure_index(
        [('username', pymongo.DESCENDING)],
        unique=True
    )
    m.db.users.ensure_index(
        [('email', pymongo.DESCENDING)],
        unique=True
    )
    # Set TTL indexes for newly created users (24 hour TTL)
    m.db.users.ensure_index(
        [('ttl', pymongo.DESCENDING)],
        expireAfterSeconds=k.EXPIRE_24HRS
    )

    # Post indexes
    # Allow us to see all posts made by a user
    m.db.posts.ensure_index(
        [('user_id', pymongo.DESCENDING)]
    )
    # Allow us to find all replies on a post
    m.db.posts.ensure_index(
        [('reply_to', pymongo.DESCENDING)]
    )
    # Index hash tags within posts
    m.db.posts.ensure_index(
        [('hashtags.hashtag', pymongo.DESCENDING)]
    )
