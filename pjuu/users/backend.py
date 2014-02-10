# -*- coding: utf-8 -*-
# Stdlib imports
from time import gmtime
from calendar import timegm
# Pjuu imports
from pjuu import app, redis as r
from pjuu.auth import current_user
from pjuu.lib.pagination import Pagination
from pjuu.posts.backend import get_post


def get_profile(uid):
    """
    Returns a users profile as Dict.
    """
    profile = r.hgetall('user:%d' % uid)
    profile['post_count'] = r.llen('posts:%d' % uid)
    profile['followers_count'] = r.zcard('followers:%d' % uid)
    profile['following_count'] = r.zcard('following:%d' % uid)
    return profile


def get_feed(uid, page=1):
    """
    Returns a users feed as a Pagination.
    """
    per_page = app.config['FEED_ITEMS_PER_PAGE']
    total = r.llen('feed:%d' % uid)
    pids = r.lrange('feed:%d' % uid, 0, 50)
    posts = []
    for pid in pids:
        posts.append(get_post(pid))
    return Pagination(posts, total, page, per_page)


def get_posts(uid, page=1):
    """
    Returns a users posts as a Pagination.
    """
    per_page = app.config['PROFILE_ITEMS_PER_PAGE']
    total = r.llen('posts:%d' % uid)
    pids = r.lrange('posts:%d' % uid, 0, 50)
    posts = []
    for pid in pids:
        posts.append(get_post(pid))
    return Pagination(posts, total, page, per_page)


def get_following(uid, page=1):
    """
    Returns a list of users uid is following as a Pagination.
    """
    pass


def get_followers(uid, page=1):
    """
    Returns a list of users whom follow uid as a Pagination.
    """
    pass


def follow_user(who_uid, whom_uid):
    """
    Add whom to who's following set and who to whom's followers set
    """
    who_uid = int(who_uid)
    whom_uid = int(whom_uid)
    if r.zrank('following:%d' % who_uid, whom_uid):
        return False
    # Follow user
    r.zadd('following:%d' % who_uid, whom_uid,
           timegm(gmtime()))
    r.zadd('followers:%d' % whom_uid, who_uid,
           timegm(gmtime()))
    return True


def unfollow_user(who_uid, whom_uid):
    """
    Remove whom from whos following set and remove who from whoms followers set
    """
    if not r.zrank('following:%d' % who_uid, whom_uid):
        return False
    # Delete uid from who following and whom followers
    r.zrem('following:%d' % who_uid, whom_uid)
    r.zrem('followers:%d' % whom_uid, who_uid)
    return True


def is_following(who_uid, whom_uid):
    """
    Check to see if who is following whom. These need to be uids
    """
    return True if r.zrank("following:%s" % who_id, whom_id) else False