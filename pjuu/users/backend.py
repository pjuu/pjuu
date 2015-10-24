# -*- coding: utf-8 -*-

"""Simple functions for handling user changes (followers, feeds, etc...) in
Redis and MongoDB.

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2015 Joe Doherty

"""

import re

from flask import current_app as app, url_for
import gridfs
from jinja2.filters import do_capitalize
import pymongo

from pjuu import mongo as m, redis as r
from pjuu.auth.utils import get_user
from pjuu.lib import keys as k, timestamp, fix_url
from pjuu.lib.alerts import BaseAlert, AlertManager
from pjuu.lib.pagination import Pagination
from pjuu.lib.uploads import process_upload
from pjuu.posts.backend import back_feed


# Regular expressions
SEARCH_PATTERN = r'[^\w]'
SEARCH_RE = re.compile(SEARCH_PATTERN)


class FollowAlert(BaseAlert):
    """A simple class for a following alert."""

    def prettify(self, for_uid=None):
        return '<a href="{0}">{1}</a> has started following you' \
               .format(url_for('users.profile',
                               username=self.user.get('username')),
                       do_capitalize(self.user.get('username')))


def get_profile(user_id):
    """Returns a user dict with add post_count, follow_count and following."""
    profile = m.db.users.find_one({'_id': user_id})

    if profile:
        # Count the users posts in MongoDB
        profile['post_count'] = m.db.posts.find(
            {'user_id': user_id, 'reply_to': {'$exists': False}}
        ).count()
        # Count followers and folowees in Redis
        profile['followers_count'] = r.zcard(k.USER_FOLLOWERS.format(user_id))
        profile['following_count'] = r.zcard(k.USER_FOLLOWING.format(user_id))

    return profile if profile else None


def get_feed(user_id, page=1, per_page=None):
    """Returns all the posts in a users feed as a pagination object.

    .. note: The feed is stored inside Redis still as this requires fan-out to
             update all the users who are following you.
    """
    if per_page is None:
        per_page = app.config.get('FEED_ITEMS_PER_PAGE')

    # Get the total number of item in the feed and the subset for the current
    # page.
    total = r.zcard(k.USER_FEED.format(user_id))
    pids = r.zrevrange(k.USER_FEED.format(user_id), (page - 1) * per_page,
                       (page * per_page) - 1)

    # Get all the posts in one call to MongoDB
    posts = []
    cursor = m.db.posts.find({'_id': {'$in': pids}}).sort(
        'created', pymongo.DESCENDING)

    for post in cursor:
        posts.append(post)

    # Get a list of unique `user_id`s from all the post.
    user_ids = list(set([post.get('user_id') for post in posts]))
    cursor = m.db.users.find({'_id': {'$in': user_ids}}, {'email': True})
    # Create a lookup dict `{username: email}`
    user_emails = dict((user.get('_id'), user.get('email')) for user in cursor)

    # Add the e-mails to the posts
    processed_posts = []
    for post in posts:
        post['user_email'] = user_emails.get(post.get('user_id'))
        processed_posts.append(post)

    # Clean up the list in Redis if the
    if len(processed_posts) < len(pids):
        diff_pids = list(
            set(pids) - set([post.get('_id') for post in processed_posts]))
        r.zrem(k.USER_FEED.format(user_id), *diff_pids)

    return Pagination(processed_posts, total, page, per_page)


def remove_from_feed(post_id, user_id):
    """Remove ``post_id`` from ``user_id``s feed."""
    return bool(r.zrem(k.USER_FEED.format(user_id), post_id))


def follow_user(who_uid, whom_uid):
    """Add whom to who's following zset and who to whom's followers zset.
    Generate an alert for this action.
    """
    # Check that we are not already following the user
    if r.zrank(k.USER_FOLLOWING.format(who_uid), whom_uid) is not None:
        return False

    # Follow user
    # Score is based on UTC epoch time
    r.zadd(k.USER_FOLLOWING.format(who_uid), timestamp(), whom_uid)
    r.zadd(k.USER_FOLLOWERS.format(whom_uid), timestamp(), who_uid)

    # Create an alert and inform whom that who is now following them
    alert = FollowAlert(who_uid)
    AlertManager().alert(alert, [whom_uid])

    # Back fill the who's feed with some posts from whom
    back_feed(who_uid, whom_uid)

    return True


def unfollow_user(who_uid, whom_uid):
    """Remove whom from who's following zset and who to whom's followers zset.
    """
    # Check that we are actually following the users
    if r.zrank(k.USER_FOLLOWING.format(who_uid), whom_uid) is None:
        return False

    # Delete uid from who following and whom followers
    r.zrem(k.USER_FOLLOWING.format(who_uid), whom_uid)
    r.zrem(k.USER_FOLLOWERS.format(whom_uid), who_uid)

    return True


def get_following(uid, page=1, per_page=None):
    """Returns a list of users uid is following as a pagination object."""
    if per_page is None:
        per_page = app.config.get('FEED_ITEMS_PER_PAGE')

    total = r.zcard(k.USER_FOLLOWING.format(uid))
    fids = r.zrevrange(k.USER_FOLLOWING.format(uid), (page - 1) * per_page,
                       (page * per_page) - 1)
    users = []
    for fid in fids:
        user = get_user(fid)
        if user:
            users.append(user)
        else:
            # Self cleaning sorted sets
            r.zrem(k.USER_FOLLOWING.format(uid), fid)
            total = r.zcard(k.USER_FOLLOWING.format(id))

    return Pagination(users, total, page, per_page)


def get_followers(uid, page=1, per_page=None):
    """Returns a list of users who follow user with uid as a pagination object.

    """
    if per_page is None:
        per_page = app.config.get('FEED_ITEMS_PER_PAGE')

    total = r.zcard(k.USER_FOLLOWERS.format(uid))
    fids = r.zrevrange(k.USER_FOLLOWERS.format(uid), (page - 1) * per_page,
                       (page * per_page) - 1)
    users = []
    for fid in fids:
        user = get_user(fid)
        if user:
            users.append(user)
        else:
            # Self cleaning sorted sets
            r.zrem(k.USER_FOLLOWERS.format(uid), fid)
            total = r.zcard(k.USER_FOLLOWERS.format(uid))

    return Pagination(users, total, page, per_page)


def is_following(who_id, whom_id):
    """Check to see if who is following whom.

    """
    if r.zrank(k.USER_FOLLOWING.format(who_id), whom_id) is not None:
        return True
    return False


# TODO Fix this!
def search(query):
    """Search for users. Will return a list as a pagination object.

    .. note: Will block Redis whilst it runs.
    """
    per_page = app.config.get('FEED_ITEMS_PER_PAGE')

    # Clean up query string
    query = query.lower()
    query = SEARCH_RE.sub('', query)

    # Lets try and find some users
    if len(query) > 0:
        # We will concatenate the glob pattern to the query
        cursor = m.db.users.find(
            {'username': {'$regex': '^{}'.format(query)}}).limit(per_page)

        # Get the total number of documents returned
        total = 0
        results = []
        for user in cursor:
            total += 1
            results.append(user)
    else:
        # If there was not query to search for 0 off everything
        results = []
        total = 0

    # Return our pagination object
    return Pagination(results, total, 1, per_page)


def update_profile_settings(user_id, about="", hide_feed_images=False,
                            feed_size=25, replies_size=25, alerts_size=50,
                            homepage='', location='', upload=None):
    """Update all options on a users profile settings in MongoDB."""
    # Ensure the homepage URL is as valid as it can be
    if homepage != '':
        homepage = fix_url(homepage)

    avatar = None
    if upload:
        filename = process_upload(user_id, upload, collection='avatars',
                                  image_size=(96, 96))
        if filename is not None:  # pragma: no cover
            avatar = filename

    update_dict = {
        'about': about,
        'hide_feed_images': hide_feed_images,
        'feed_pagination_size': int(feed_size),
        'replies_pagination_size': int(replies_size),
        'alerts_pagination_size': int(alerts_size),
        'homepage': homepage,
        'location': location,
    }

    if avatar is not None:
        # Add the avatar to the dict
        update_dict['avatar'] = avatar

        # Clean up any old avatars
        # There is no update in GridFS
        grid = gridfs.GridFS(m.db, collection='avatars')
        # Get all old ones
        cursor = grid.find(
            {'filename': avatar}).sort('uploadDate', -1).skip(1)
        for f in cursor:
            grid.delete(f._id)

    # Update the users profile
    m.db.users.update({'_id': user_id}, {'$set': update_dict})

    # Return the user object. We can update the current_user from this
    return get_user(user_id)


def get_alerts(user_id, page=1, per_page=None):
    """Return a list of alert objects as a pagination.

    """
    if per_page is None:
        per_page = app.config.get('ALERT_ITEMS_PER_PAGE')

    # Get the last time the users checked the alerts
    # Try and cast the value to an int so we can boolean compare them
    try:
        alerts_last_checked = m.db.users.find_one(
            {'_id': user_id}
        ).get('alerts_last_checked')
    except (AttributeError, TypeError, ValueError):
        alerts_last_checked = 0

    # Get total number of elements in the sorted set
    total = r.zcard(k.USER_ALERTS.format(user_id))
    aids = r.zrevrange(k.USER_ALERTS.format(user_id), (page - 1) * per_page,
                       (page * per_page) - 1)

    # Create AlertManager to load the alerts
    am = AlertManager()

    alerts = []

    for aid in aids:
        # Load the alert in to the alert manager
        alert = am.get(aid)
        if alert:
            # Check to see if the alert is newer than the time we last checked.
            # This allows us to highlight in the template
            # This will assign a new property to the object: `new`
            if int(alert.timestamp) > alerts_last_checked:
                alert.new = True

            # Add the entire alert from the manager on the list
            alerts.append(alert)
        else:
            # Self cleaning zset
            r.zrem(k.USER_ALERTS.format(user_id), aid)
            total = r.zcard(k.USER_ALERTS.format(user_id))
            # May as well delete the alert if there is one
            r.delete(k.ALERT.format(aid))

    # Update the last time the user checked there alerts
    # This will allow us to alert a user too new alerts with the /i-has-alerts
    # url
    m.db.users.update({'_id': user_id},
                      {'$set': {'alerts_last_checked': timestamp()}})

    return Pagination(alerts, total, page, per_page)


def delete_alert(user_id, alert_id):
    """Removes an alert with aid from user with uid's alert feed. This does not
    delete the alert object, it may be on other users feeds.

    """
    return bool(r.zrem(k.USER_ALERTS.format(user_id), alert_id))


def new_alerts(user_id):
    """Checks too see if user has any new alerts since they last got the them.

    """
    # Get the stamp since last check from Redis
    # If this has not been called before make it 0
    alerts_last_checked = get_user(user_id).get('alerts_last_checked', 0)

    # Do the check. This will just see if there is anything returned from the
    # sorted set newer than the last_checked timestamp, SIMPLES.
    #
    # Note: zrevrangebyscore has max and min the wrong way round :P
    return bool(r.zrevrangebyscore(k.USER_ALERTS.format(user_id), '+inf',
                alerts_last_checked, start=0, num=1))
