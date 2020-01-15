# -*- coding: utf-8 -*-

"""Simple functions for handling user changes (followers, feeds, etc...) in
Redis and MongoDB.

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2020 Joe Doherty

"""

import re

from flask import current_app as app, url_for
from jinja2.filters import do_capitalize
import pymongo

from pjuu import mongo as m, redis as r
from pjuu.auth.utils import get_user
from pjuu.lib import keys as k, timestamp, fix_url
from pjuu.lib.alerts import BaseAlert, AlertManager
from pjuu.lib.pagination import Pagination
from pjuu.lib.uploads import process_upload, delete_upload
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


def get_user_permission(who_id, whom_id):
    """Returns the permission level user with `who_id` has when looking at
    `whom_id`'s profile/posts.

    :param who_id: User to get permissions of
    :type who_id: str
    :param whom_id: User to check against what permission `who_id` has
    :type whom_id: str
    :rtype: int

    """
    if who_id is not None and whom_id is not None:
        if who_id == whom_id or is_trusted(who_id, whom_id):
            return k.PERM_APPROVED
        else:
            return k.PERM_PJUU

    return k.PERM_PUBLIC


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
        profile['trusted_count'] = r.zcard(k.USER_APPROVED.format(user_id))

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
    cursor = m.db.users.find({'_id': {'$in': user_ids}},
                             {'avatar': True, 'donated': True})

    users = dict((user.get('_id'), {
        'avatar': user.get('avatar'),
        'donated': user.get('donated', False)
    }) for user in cursor)

    processed_posts = []
    for post in posts:
        post['user_avatar'] = users.get(post.get('user_id')).get('avatar')
        post['user_donated'] = users.get(post.get('user_id')).get('donated')
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


def top_users_by_score(limit=5):
    """Get the top 5 users by score.
    Used to show names on the welcome message.
    """
    cursor = m.db.users.find(
        {}, {'_id': -1, 'username': 1}).sort('score', -1).limit(limit)
    users = []
    for user in cursor:
        users.append(user)
    return users


def follow_user(who_uid, whom_uid):
    """Add whom to who's following zset and who to whom's followers zset.
    Generate an alert for this action.
    """
    # Check that we are not already following the user
    if r.zrank(k.USER_FOLLOWING.format(who_uid), str(whom_uid)) is not None:
        return False

    # Follow user
    # Score is based on UTC epoch time
    r.zadd(k.USER_FOLLOWING.format(who_uid), {str(whom_uid): timestamp()})
    r.zadd(k.USER_FOLLOWERS.format(whom_uid), {str(who_uid): timestamp()})

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

    # Delete the user from the approved list
    unapprove_user(whom_uid, who_uid)

    return True


def approve_user(who_uid, whom_uid):
    """Allow a user to approve a follower"""
    # Check that the user is actually following.
    # Fail if not
    if r.zrank(k.USER_FOLLOWERS.format(who_uid), whom_uid) is None:
        return False

    # Add the user to the approved list
    # No alert is generated
    r.zadd(k.USER_APPROVED.format(who_uid), {str(whom_uid): timestamp()})

    return True


def unapprove_user(who_uid, whom_uid):
    """Allow a user to un-approve a follower"""
    # Check the follower is actually approved
    if r.zrank(k.USER_APPROVED.format(who_uid), whom_uid) is None:
        return False

    # No alert for un-approved
    r.zrem(k.USER_APPROVED.format(who_uid), whom_uid)

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


def get_trusted(uid, page=1, per_page=None):
    """Returns a list of users who a user trusts.

    """
    if per_page is None:
        per_page = app.config.get('FEED_ITEMS_PER_PAGE')

    total = r.zcard(k.USER_APPROVED.format(uid))
    fids = r.zrevrange(k.USER_APPROVED.format(uid), (page - 1) * per_page,
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


def is_trusted(who_id, whom_id):
    """Is the current user approved by the user with who_id"""
    if r.zrank(k.USER_APPROVED.format(who_id), whom_id) is not None:
        return True
    return False


def search(query, page=1, per_page=None):
    """Search for users / hashtagged posts (not replies)."""
    if per_page is None:
        per_page = app.config.get('FEED_ITEMS_PER_PAGE')

    # TODO: Refactor the max size of search items away
    max_items = app.config.get('MAX_SEARCH_ITEMS', 500)

    # Clean up query string
    query = query.lower().strip()

    search_hashtags = True
    search_users = True

    if query.startswith('@'):
        search_hashtags = False
    elif query.startswith('#'):
        search_users = False

    query = SEARCH_RE.sub('', query)

    if len(query) > 0:
        # Get the total number of documents returned
        results = []
        total = 0

        users = []
        if search_users:
            # We will concatenate the glob pattern to the query
            cursor = m.db.users.find({
                'username': {'$regex': '^{}'.format(query)},
                'active': True
            }).sort(
                'username', pymongo.ASCENDING
            ).limit(max_items)

            # You can count the length of the cursor
            total += cursor.count()

            for user in cursor:
                users.append(user)

        posts = []
        if search_hashtags:
            cursor = m.db.posts.find({
                'hashtags.hashtag': {'$regex': '^{}'.format(query)},
                'reply_to': {'$exists': False}
            }).sort(
                'hashtags.hashtag', pymongo.ASCENDING
            ).limit(max_items)

            total += cursor.count()

            preprocessed_posts = []
            user_ids = []

            for hashtag in cursor:
                user_ids.append(hashtag.get('user_id'))
                preprocessed_posts.append(hashtag)

            cursor = m.db.users.find({'_id': {'$in': user_ids}},
                                     {'avatar': True, 'donated': True})

            post_users = dict((user.get('_id'), {
                'avatar': user.get('avatar'),
                'donated': user.get('donated', False)
            }) for user in cursor)

            # Add the e-mails to the posts
            for post in preprocessed_posts:
                post['user_avatar'] = \
                    post_users.get(post.get('user_id')).get('avatar')
                post['user_donated'] = \
                    post_users.get(post.get('user_id')).get('donated')
                posts.append(post)

        results = users + posts

        def sort_results(k):
            """Allow sorting of the search results by closest matchng
            then by date the item was created."""
            if k.get('hashtags'):
                for hashtag in k.get('hashtags'):  # pragma: no branch
                    if hashtag.get('hashtag', '').startswith(query):
                        return (hashtag.get('hashtag'),
                                timestamp() - k.get('created', 0))
            else:
                return (k.get('username'),
                        timestamp() - k.get('created', 0))

        results = sorted(results, key=sort_results)

        # Limit the mount of items in the response
        results = results[(page - 1) * per_page:page * per_page]

    else:
        # If there was not query to search for 0 off everything
        results = []
        total = 0

    # Return our pagination object
    return Pagination(results, total, page, per_page)


def update_profile_settings(user_id, about="", hide_feed_images=False,
                            feed_size=25, replies_size=25, alerts_size=50,
                            reply_sort_order=-1, homepage='', location='',
                            upload=None, permission=0):
    """Update all options on a users profile settings in MongoDB."""
    # Ensure the homepage URL is as valid as it can be
    if homepage != '':
        homepage = fix_url(homepage)

    avatar = None
    if upload:
        filename, _ = process_upload(upload, image_size=(96, 96),
                                     thumbnail=False)
        if filename is not None:  # pragma: no cover
            avatar = filename

    update_dict = {
        'about': about,
        'hide_feed_images': hide_feed_images,
        'feed_pagination_size': int(feed_size),
        'replies_pagination_size': int(replies_size),
        'alerts_pagination_size': int(alerts_size),
        'reply_sort_order': reply_sort_order,
        'homepage': homepage,
        'location': location,
        'default_permission': int(permission)
    }

    if avatar is not None:
        update_dict['avatar'] = avatar

        user = get_user(user_id)

        if user.get('avatar'):
            # Clean up any old avatars
            # There is no update in GridFS
            delete_upload(user.get('avatar'))

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
    return len(r.zrevrangebyscore(k.USER_ALERTS.format(user_id), '+inf',
               alerts_last_checked))


def remove_tip(user_id, tip_name):
    """Sets the tip with `tip_name` to False so it doesn't show

    .. note: The tipname needs to be checked at the front end
    """
    return m.db.users.update({'_id': user_id}, {'$set': {
        'tip_{}'.format(tip_name): False
    }})


def reset_tips(user_id):
    """Reset all tips as if you had never seen them"""
    update_dict = {}

    # Create a Mongo update dictionary of all VALID_TIP_NAMES
    for tip_name in k.VALID_TIP_NAMES:
        update_dict['tip_{}'.format(tip_name)] = True

    m.db.users.update({'_id': user_id}, {'$set': update_dict})
    return True
