# -*- coding: utf-8 -*-

"""
Description:
    Pjuu post backend system. Everything which deals with Redis in the users
    package is here, aswell as some helper functions to keep the code clean

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
from time import gmtime
from calendar import timegm
import re
# 3rd party imports
from flask import current_app as app, url_for
from jinja2.filters import do_capitalize
# Pjuu imports
from pjuu import redis as r
from pjuu.auth.backend import get_user, USERNAME_RE
from pjuu.lib import keys as K, lua as L, timestamp
from pjuu.lib.alerts import BaseAlert, AlertManager
from pjuu.lib.pagination import Pagination
from pjuu.posts.backend import (get_comment, get_post, delete_comment,
                                delete_post)


# Regular expressions
SEARCH_PATTERN = r'[^\w]'
SEARCH_RE = re.compile(SEARCH_PATTERN)


class FollowAlert(BaseAlert):
    """A following alert

    """

    def prettify(self, for_uid=None):
        return '<a href="{0}">{1}</a> has started following you' \
               .format(url_for('profile', username=self.get_username()),
                       do_capitalize(self.get_username()))

def get_profile(uid):
    """Returns a user dict with add post_count, follow_count and following.

    """
    profile = r.hgetall(K.USER.format(uid))

    if profile:
        profile['post_count'] = r.llen(K.USER_POSTS.format(uid))
        profile['followers_count'] = r.zcard(K.USER_FOLLOWERS.format(uid))
        profile['following_count'] = r.zcard(K.USER_FOLLOWING.format(uid))

    return profile if profile else None


def get_feed(uid, page=1):
    """Returns a users feed as a pagination object.

    """
    per_page = app.config.get('FEED_ITEMS_PER_PAGE')
    total = r.llen(K.USER_FEED.format(uid))
    pids = r.lrange(K.USER_FEED.format(uid), (page - 1) * per_page,
                    (page * per_page) - 1)
    posts = []
    for pid in pids:
        # Get the post
        post = get_post(pid)
        if post:
            posts.append(post)
        else:
            # Self cleaning lists
            r.lrem(K.USER_FEED.format(uid), 1, pid)
            total = r.llen(K.USER_FEED.format(uid))

    return Pagination(posts, total, page, per_page)


def get_posts(uid, page=1):
    """Returns a users posts as a pagination object.

    """
    per_page = app.config.get('PROFILE_ITEMS_PER_PAGE')
    total = r.llen(K.USER_POSTS.format(uid))
    pids = r.lrange(K.USER_POSTS.format(uid), (page - 1) * per_page,
                    page * per_page)
    posts = []
    for pid in pids:
        # Get the post
        post = get_post(pid)
        if post:
            posts.append(post)
        else:
            # Self cleaning lists
            r.lrem(K.USER_POSTS.format(uid), 0, pid)
            total = r.llen(K.USER_POSTS.format(uid))

    return Pagination(posts, total, page, per_page)


def get_comments(pid, page=1):
    """Returns all a posts comments as a pagination object.
    """
    per_page = app.config.get('PROFILE_ITEMS_PER_PAGE')
    total = r.llen(K.POST_COMMENTS.format(pid))
    cids = r.lrange(K.POST_COMMENTS.format(pid), (page - 1) * per_page,
                    (page * per_page) - 1)
    comments = []
    for cid in cids:
        # Get the comment
        comment = get_comment(cid)
        if comment is not None:
            comments.append(comment)
        else:
            # Self cleaning lists
            r.lrem(K.POST_COMMENTS.format(pid), 0, cid)
            total = r.llen(K.POST_COMMENTS.format(cid))

    return Pagination(comments, total, page, per_page)


def follow_user(who_uid, whom_uid):
    """Add whom to who's following zset and who to whom's followers zset.
    Generate an alert for this action.

    """
    # Check that we are not already following the user
    if r.zrank(K.USER_FOLLOWING.format(who_uid), whom_uid) is not None:
        return False

    # Follow user
    # Score is based on UTC epoch time
    r.zadd(K.USER_FOLLOWING.format(who_uid), timestamp(), whom_uid)
    r.zadd(K.USER_FOLLOWERS.format(whom_uid), timestamp(), who_uid)

    # Create an alert and inform whom that who is now following them
    alert = FollowAlert(who_uid)
    AlertManager().alert(alert, [whom_uid])

    return True


def unfollow_user(who_uid, whom_uid):
    """Remove whom from who's following zset and who to whom's followers zset

    """
    # Check that we are actually following the users
    if r.zrank(K.USER_FOLLOWING.format(who_uid), whom_uid) is None:
        return False

    # Delete uid from who following and whom followers
    r.zrem(K.USER_FOLLOWING.format(who_uid), whom_uid)
    r.zrem(K.USER_FOLLOWERS.format(whom_uid), who_uid)

    return True


def get_following(uid, page=1):
    """Returns a list of users uid is following as a pagination object.

    """
    per_page = app.config.get('PROFILE_ITEMS_PER_PAGE')
    total = r.zcard(K.USER_FOLLOWING.format(uid))
    fids = r.zrange(K.USER_FOLLOWING.format(uid), (page - 1) * per_page,
                    (page * per_page) - 1)
    users = []
    for fid in fids:
        # Get user
        user = get_user(fid)
        if user:
            users.append(user)
        else:
            # Self cleaning sorted sets
            r.zrem(K.USER_FOLLOWING.format(uid), fid)
            total = r.zcard(K.USER_FOLLOWING.format(id))

    return Pagination(users, total, page, per_page)


def get_followers(uid, page=1):
    """Returns a list of users who follow user with uid as a pagination object.

    """
    per_page = app.config.get('PROFILE_ITEMS_PER_PAGE')
    total = r.zcard(K.USER_FOLLOWERS.format(uid))
    fids = r.zrange(K.USER_FOLLOWERS.format(uid), (page - 1) * per_page,
                    (page * per_page) - 1)
    users = []
    for fid in fids:
        # Get user
        user = get_user(fid)
        if user:
            users.append(user)
        else:
            # Self cleaning sorted sets
            r.zrem(K.USER_FOLLOWERS.format(uid), fid)
            total = r.zcard(K.USER_FOLLOWERS.format(uid))

    return Pagination(users, total, page, per_page)


def is_following(who_uid, whom_uid):
    """Check to see if who is following whom.

    """
    if r.zrank(K.USER_FOLLOWING.format(who_uid), whom_uid) is not None:
        return True
    return False


# TODO Fix this!
def search(query):
    """Search for users. Will return a list as a pagination object.
    Please note that this will block redis whilst it runs.

    """
    per_page = app.config.get('PROFILE_ITEMS_PER_PAGE')
    # Clean up query string
    query = query.lower()
    query = SEARCH_RE.sub('', query)
    # Lets find and get the users
    if len(query) > 0:
        # We will concatenate the glob pattern to the query
        keys = r.keys(K.UID_USERNAME.format(query + '*'))
    else:
        keys = []

    # Get results from the keys, only show a maximum of per_page in a search.
    # It could change too much between pages to be stable
    # We will simply trim the keys list to this value, it's easier :)
    keys = keys[:per_page]
    results = []
    for key in keys:
        user = get_user(r.get(key))
        # Ensure the user exists before adding to the list and is not
        # a deleted accoumt remnant, it shouldn't be!
        if user:
            results.append(user)

    # Get the total number of users being returned
    total = len(results)

    return Pagination(results, total, 1, per_page)


def set_about(uid, about):
    """Set a users about message.

    """
    return r.hset(K.USER.format(uid), 'about', about)


def get_alerts(uid, page=1):
    """Return a list of alert objects as a pagination.

    """
    # Update the last time the user checked there alerts
    # This will allow us to alert a user too new alerts with the /i-has-alerts
    # url
    r.hset(K.USER.format(uid), 'alerts_last_checked', timestamp())

    per_page = app.config.get('ALERT_ITEMS_PER_PAGE')

    # Get total number of elements in the sorted set
    total = r.zcard(K.USER_ALERTS.format(uid))
    aids = r.zrevrange(K.USER_ALERTS.format(uid), (page - 1) * per_page,
                       (page * per_page) - 1)

    # Create AlertManager to load the alerts
    am = AlertManager()

    alerts = []
    for aid in aids:
        # Load the alert in to the alert manager
        alert = am.get(aid)
        if alert:
            # Add the entire alert from the manager on the list
            alerts.append(alert)
        else:
            # Self cleaning zset
            r.zrem(K.USER_ALERTS.format(uid), aid)
            total = r.zcard(K.USER_ALERTS.format(uid))
            # May as well delete the alert if there is one
            r.delete(K.ALERT.format(aid))

    return Pagination(alerts, total, page, per_page)


def delete_alert(uid, aid):
    """Removes an alert with aid from user with uid's alert feed. This does not
    delete the alert object, it may be on other users feeds.

    """
    return bool(r.zrem(K.USER_ALERTS.format(uid), aid))


def i_has_alerts(uid):
    """Checks too see if user has any new alerts since they last got the them.

    """
    # Get the stamp since last check from Redis
    # If this has not been called before make it 0
    alerts_last_checked = \
        r.hget(K.USER.format(uid), 'alerts_last_checked') or 0

    # Do the check. This will just see if there is anything returned from the
    # sorted set newer than the last_checked timestamp, SIMPLES.
    #
    # Note: zrevrangebyscore has max and min the wrong way round :P
    return bool(r.zrevrangebyscore(K.USER_ALERTS.format(uid), '+inf',
                alerts_last_checked, start=0, num=1))
