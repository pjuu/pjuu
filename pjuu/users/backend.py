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
from pjuu.lib import keys as K, lua as L, timestamp
from pjuu.lib.alerts import BaseAlert, AlertManager
from pjuu.lib.pagination import Pagination
from pjuu.auth.backend import get_user
from pjuu.posts.backend import get_comment, get_post


class FollowAlert(BaseAlert):
    """
    Form for a FollowAlert, very simple, pretty much a lib.alerts.BaseAlert
    """

    def prettify(self):
        return '<a href="{0}">{1}</a> has started following you' \
               .format(url_for('profile', username=self.get_username()),
                       do_capitalize(self.get_username()))

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
        # Get the post
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
    total = r.llen(K.USER_POSTS % uid)
    pids = r.lrange(K.USER_POSTS % uid, (page - 1) * per_page,
                    page * per_page)
    posts = []
    for pid in pids:
        # Get the post
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
        # Change unicode number to int
        cid = int(cid)
        # Get the comment
        comment = get_comment(cid)
        if comment is not None:
            comments.append(comment)
        else:
            # Self cleaning lists
            r.lrem(K.POST_COMMENTS % pid, 1, cid)
            total = r.llen(K.POST_COMMENTS % cid)

    return Pagination(comments, total, page, per_page)


def follow_user(who_uid, whom_uid):
    """
    Add whom to who's following set and who to whom's followers set
    """
    who_uid = int(who_uid)
    whom_uid = int(whom_uid)
    if r.zrank(K.USER_FOLLOWING % who_uid, whom_uid) is not None:
        return False
    # Follow user
    # Score is based on UTC epoch time
    r.zadd(K.USER_FOLLOWING % who_uid, timestamp(), whom_uid)
    r.zadd(K.USER_FOLLOWERS % whom_uid, timestamp(), who_uid)

    # Create an alert and inform whom that who is now following them
    alert = FollowAlert(who_uid)
    am = AlertManager(alert)
    am.alert_user(whom_uid)

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
        # Get user
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
        # Get user
        user = get_user(fid)
        if user:
            users.append(user)
        else:
            # Self cleaning sorted sets
            r.zrem(K.USER_FOLLOWERS % uid, fid)
            total = r.zcard(K.USER_FOLLOWERS % uid)

    return Pagination(users, total, page, per_page)


def is_following(who_uid, whom_uid):
    """
    Check to see if who is following whom. These need to be uids
    """
    who_uid = int(who_uid)
    whom_uid = int(whom_uid)
    if r.zrank(K.USER_FOLLOWING % who_uid, whom_uid) is not None:
        return True
    return False


# TODO Fix this!
def search(query):
    """
    Handles searching for users. This is inefficient; O(n) it will
    not scale to full production.

    This will also BLOCK Redis why it runs
    """
    per_page = app.config['PROFILE_ITEMS_PER_PAGE']
    # Clean up query string
    query = query.lower()
    username_re = re.compile('[^a-zA-Z0-9_]+')
    query = username_re.sub('', query)
    # Lets find and get the users
    if len(query) > 0:
        # We will concatenate the glob pattern to the query
        keys = r.keys(K.UID_USERNAME % (query + '*'))
    else:
        keys = []

    # Get results from the keys, only show a maximum of per_page is a search.
    # It could change too much between pages to be stable
    # We will simply trim the keys list to this value, it's easier :)
    keys = keys[:per_page]
    results = []
    for key in keys:
        user = get_user(r.get(key))
        # Ensure the user exists before adding to the list and is not
        # a deleted accoumt remnant
        if user:
            results.append(user)

    total = len(results)

    return Pagination(results, total, 1, per_page)


def set_about(uid, about):
    """
    Set a users about message on their profile.

    This is a simple Redis operation but is here so all Redis actions are in
    the backends
    """
    uid = int(uid)
    # Set the about message for the user in their hash
    r.hset(K.USER % uid, 'about', about)


def get_alerts(uid, page=1):
    """
    Return a paginated list of alert objects.

    Note: Due to the fact that we are storing alerts in a sorted set we can not
          set an expire. These will need to be expired manually, which happens
          everytime this is called. This way there should be a minimal number
          of call to ZREMRANGEBYSCORE.

          Alerts are stored for 4 weeks. We store nothing more than IDs within
          the objects so there should be no privacy concerns.
    """
    uid = int(uid)

    # Update the last time the user checked there alerts
    # This will allow us to alert a user too new alerts with the /i-has-alerts
    # url
    r.hset(K.USER % uid, 'alerts_last_checked', timestamp())

    per_page = app.config['ALERT_ITEMS_PER_PAGE']

    # Before we get totals we will clean the sorted set to remove any
    # data older than 4 weeks.
    # This cleans the oldest to the newest
    r.zremrangebyscore(K.USER_ALERTS % uid, '-inf',
                       timestamp() - K.EXPIRE_4WKS)

    # Get total number of elements in the sorted set
    total = r.zcard(K.USER_ALERTS % uid)
    # Called aids as legacy, there is no such thing as an alert id
    # We use REVRANGE as alerts should be newest to oldest
    alert_dumps = r.zrevrange(K.USER_ALERTS % uid, (page - 1) * per_page,
                              (page * per_page) - 1)

    # Create AlertManager to load the alerts
    am = AlertManager()

    alerts = []
    for alert_dump in alert_dumps:
        # Load the alert in to the alert manager
        am.loads(alert_dump)
        if am.alert:
            # Add the entire alert from the manager on the list
            alerts.append(am.alert)
        else:
            # Self cleaning zset
            r.zrem(K.USER_ALERTS % uid, 1, alert_dump)
            total = r.zcard(K.USER_ALERTS % uid)

    return Pagination(alerts, total, page, per_page)


def i_has_alerts(uid):
    """
    Checks too see if user has any new alerts since they last visited the
    /alerts endoint
    """
    uid = int(uid)

    # Get the stamp since last check from Redis
    # If this has not been called before make it 0
    alerts_last_checked = r.hget(K.USER % uid, 'alerts_last_checked') or 0

    # Do the check. This will just see if there is anything returned from the
    # sorted set newer than the last_checked timestamp, SIMPLES.
    #
    # Note: zrevrangebyscore has max and min the wrong way round :P
    return bool(r.zrevrangebyscore(K.USER_ALERTS % uid, '+inf',
                alerts_last_checked, start=0, num=1))
