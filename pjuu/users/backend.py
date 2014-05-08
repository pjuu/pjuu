# -*- coding: utf-8 -*-

##############################################################################
# Copyright 2014 Joe Doherty <joe@pjuu.com>
#
# Pjuu is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Pjuu is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
##############################################################################

# Stdlib imports
from time import gmtime
from calendar import timegm
import re
# Pjuu imports
from pjuu import app, keys as K, lua as L, redis as r
from pjuu.lib import timestamp
from pjuu.lib.pagination import Pagination
from pjuu.posts.backend import get_comment, get_post


def get_profile(uid):
    """
    Returns a users profile as Dict.
    """
    uid = int(uid)
    profile = r.hgetall(K.USER % uid)
    if profile:
        profile['post_count'] = r.llen(K.USER_POSTS % uid)
        profile['followers_count'] = r.zcard(K.USER_FOLLOWERS % uid)
        profile['following_count'] = r.zcard(K.USER_FOLLOWING % uid)
    return profile if profile else None


def get_user(uid):
    """
    Returns a users mini-profile for lists. This is the full hash of a user
    without adding the additional information.
    """
    uid = int(uid)
    user = r.hgetall(K.USER % uid)
    return user


def get_feed(uid, page=1):
    """
    Returns a users feed as a Pagination.
    """
    per_page = app.config['FEED_ITEMS_PER_PAGE']
    total = r.llen(K.USER_FEED % uid)
    pids = r.lrange(K.USER_FEED % uid, (page - 1) * per_page,
                    (page * per_page) - 1)
    posts = []
    for pid in pids:
        post = get_post(pid)
        if post:
            posts.append(post)
        else:
            # Self cleaning lists
            r.lrem(K.USER_FEED % uid, 1, pid)
            total = r.llen(K.USER_FEED % uid)

    return Pagination(posts, total, page, per_page)


def get_posts(uid, page=1):
    """
    Returns a users posts as a Pagination.
    """
    per_page = app.config['PROFILE_ITEMS_PER_PAGE']
    total = r.llen(K.USER_POSTS)
    pids = r.lrange(K.USER_POSTS % uid, (page - 1) * per_page,
                    page * per_page)
    posts = []
    for pid in pids:
        post = get_post(pid)
        if post:
            posts.append(post)
        else:
            # Self cleaning lists
            r.lrem(K.USER_POSTS % uid, 1, pid)
            total = r.llen(K.USER_POSTS % uid)

    return Pagination(posts, total, page, per_page)


def get_comments(pid, page=1):
    """
    Returns a pagination of a posts comments
    """
    per_page = app.config['PROFILE_ITEMS_PER_PAGE']
    total = r.llen(K.POST_COMMENTS % pid)
    cids = r.lrange(K.POST_COMMENTS % pid, (page - 1) * per_page,
                    (page * per_page) - 1)
    comments = []
    for cid in cids:
        comment = get_comment(cid)
        if comment is not None:
            comments.append(comment)
        else:
            # Self cleaning lists
            r.lrem(K.USER_COMMENTS % pid, 1, cid)
            total = r.llen(K.USER_COMMENTS % cid)

    return Pagination(comments, total, page, per_page)


def get_following(uid, page=1):
    """
    Returns a list of users uid is following as a Pagination.
    """
    per_page = app.config['PROFILE_ITEMS_PER_PAGE']
    total = r.zcard(K.USER_FOLLOWING % uid)
    fids = r.zrange(K.USER_FOLLOWING % uid, (page - 1) * per_page,
                    (page * per_page) - 1)
    users = []
    for fid in fids:
        user = get_user(fid)
        if user:
            users.append(user)
        else:
            # Self cleaning sorted sets
            r.zrem(K.USER_FOLLOWING % uid, fid)
            total = r.zcard(K.USER_FOLLOWING % uid)

    return Pagination(users, total, page, per_page)


def get_followers(uid, page=1):
    """
    Returns a list of users whom follow uid as a Pagination.
    """
    per_page = app.config['PROFILE_ITEMS_PER_PAGE']
    total = r.zcard(K.USER_FOLLOWERS % uid)
    fids = r.zrange(K.USER_FOLLOWERS % uid, (page - 1) * per_page,
                    (page * per_page) - 1)
    users = []
    for fid in fids:
        user = get_user(fid)
        if user:
            users.append(user)
        else:
            # Self cleaning sorted sets
            r.zrem(K.USER_FOLLOWERS % uid, fid)
            total = r.zcard(K.USER_FOLLOWERS % uid)

    return Pagination(users, total, page, per_page)


def follow_user(who_uid, whom_uid):
    """
    Add whom to who's following set and who to whom's followers set
    """
    who_uid = int(who_uid)
    whom_uid = int(whom_uid)
    if r.zrank(K.USER_FOLLOWING % who_uid, whom_uid):
        return False
    # Follow user
    # Score is based on UTC epoch time
    r.zadd(K.USER_FOLLOWING % who_uid, timestamp(), whom_uid)
    r.zadd(K.USER_FOLLOWERS % whom_uid, timestamp(), who_uid)
    return True


def unfollow_user(who_uid, whom_uid):
    """
    Remove whom from whos following set and remove who from whoms
    followers set
    """
    who_uid = int(who_uid)
    whom_uid = int(whom_uid)
    if r.zrank(K.USER_FOLLOWING % who_uid, whom_uid) is None:
        return False
    # Delete uid from who following and whom followers
    r.zrem(K.USER_FOLLOWING % who_uid, whom_uid)
    r.zrem(K.USER_FOLLOWERS % whom_uid, who_uid)
    return True


def is_following(who_uid, whom_uid):
    """
    Check to see if who is following whom. These need to be uids
    """
    who_uid = int(who_uid)
    whom_uid = int(whom_uid)
    if r.zrank(K.USER_FOLLOWING% who_uid, whom_uid) is not None:
        return True
    else:
        return False


# TODO Fix this!
def search(query, page=1):
    """
    Handles searching for users. This is inefficient; O(n) it will
    not scale to full production
    """
    per_page = app.config['PROFILE_ITEMS_PER_PAGE']
    # Clean up query string
    query = query.lower()
    username_re = re.compile('[^a-z0-9_]+')
    query = username_re.sub('', query)
    # Lets find and get the users
    if len(query) > 0:
        keys = r.keys(K.UID_USERNAME % query)
    else:
        keys = []
    results = []
    for key in keys:
        uid = r.get(key)
        results.append(get_user(uid))
    total = len(results)

    return Pagination(results, total, page, per_page)