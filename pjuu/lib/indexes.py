# -*- coding: utf8 -*-

"""
Description:
    Creates the MongoDB indexes. This can be run each time the app is deployed
    it will have no effect on indexes which are already there.

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

# 3rd party imports
import pymongo
# Pjuu imports
from pjuu import mongo as m


def create_indexes():
    """Creates all our MongoDB indexes.

    Please note that _id fields are already indexed by MongoDB. If you need to
    lookup a document by a field that is not in here, ensure you need it! If
    it is a one off like how many users are banned it doesn't need to be here.
    If you look up by a key all the time (new feature) it will probably need to
    be indexed.

    """
    # User indexes
    # User name and e-mail address have to be unique across the database
    m.db.users.ensure_index([('username', pymongo.DESCENDING)], unique=True)
    m.db.users.ensure_index([('email', pymongo.DESCENDING)], unique=True)

    # Post indexes
    # Allow us to see all posts made by a user
    m.db.posts.ensure_index([('uid', pymongo.DESCENDING)])

    # Comment indexes
    # Allow us to look up all comments by a user (deleting and dumping acc's)
    m.db.comments.ensure_index([('uid', pymongo.DESCENDING)])
    # Allow us to find all the comments on a certain post
    m.db.comments.ensure_index([('pid', pymongo.DESCENDING)])
