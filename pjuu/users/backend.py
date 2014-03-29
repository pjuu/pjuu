# -*- coding: utf-8 -*-
# Stdlib imports
from time import gmtime
from calendar import timegm
import re
import string
# Pjuu imports
from pjuu import app, redis as r
from pjuu.lib.pagination import Pagination
from pjuu.posts.backend import get_comment, get_post


def get_profile(uid):
    """
    Returns a users profile as Dict.
    """
    profile = r.hgetall('user:%d' % uid)
    if profile:
        profile['post_count'] = r.llen('user:%d:posts' % uid)
        profile['followers_count'] = r.zcard('user:%d:followers' % uid)
        profile['following_count'] = r.zcard('user:%d:following' % uid)
    return profile


def get_user(uid):
    """
    Returns a users mini-profile for lists
    """
    uid = int(uid)
    user = r.hgetall('user:%d' % uid)
    return user


def get_feed(uid, page=1):
    """
    Returns a users feed as a Pagination.
    """
    per_page = app.config['FEED_ITEMS_PER_PAGE']
    total = r.llen('user:%d:feed' % uid)
    pids = r.lrange('user:%d:feed' % uid, (page - 1) * per_page,
                    (page * per_page) - 1)
    posts = []
    for pid in pids:
        post = get_post(pid)
        if post:
            posts.append(post)
    return Pagination(posts, total, page, per_page)


def get_posts(uid, page=1):
    """
    Returns a users posts as a Pagination.
    """
    per_page = app.config['PROFILE_ITEMS_PER_PAGE']
    total = r.llen('user:%d:posts' % uid)
    pids = r.lrange('user:%d:posts' % uid, (page - 1) * per_page,
                    page * per_page)
    posts = []
    for pid in pids:
        post = get_post(pid)
        if post:
            posts.append(post)
    return Pagination(posts, total, page, per_page)


def get_comments(pid, page=1):
    """
    Returns a pagination of a posts comments
    """
    per_page = app.config['PROFILE_ITEMS_PER_PAGE']
    total = r.llen('post:%d:comments' % pid)
    cids = r.lrange('post:%d:comments' % pid, (page - 1) * per_page,
                    (page * per_page) - 1)
    comments = []
    for cid in cids:
        comment = get_comment(cid)
        if comment:
            comments.append(comment)
    return Pagination(comments, total, page, per_page)


def get_following(uid, page=1):
    """
    Returns a list of users uid is following as a Pagination.
    """
    per_page = app.config['PROFILE_ITEMS_PER_PAGE']
    total = r.zcard('user:%d:following' % uid)
    fids = r.zrange('user:%d:following' % uid, (page - 1) * per_page,
                    (page * per_page) - 1)
    users = []
    for fid in fids:
        users.append(get_user(fid))
    return Pagination(users, total, page, per_page)


def get_followers(uid, page=1):
    """
    Returns a list of users whom follow uid as a Pagination.
    """
    per_page = app.config['PROFILE_ITEMS_PER_PAGE']
    total = r.zcard('user:%d:followers' % uid)
    fids = r.zrange('user:%d:followers' % uid, (page - 1) * per_page,
                    (page * per_page) - 1)
    users = []
    for fid in fids:
        users.append(get_user(fid))
    return Pagination(users, total, page, per_page)


def follow_user(who_uid, whom_uid):
    """
    Add whom to who's following set and who to whom's followers set
    """
    who_uid = int(who_uid)
    whom_uid = int(whom_uid)
    if r.zrank('user:%d:following' % who_uid, whom_uid):
        return False
    # Follow user
    # Score is based on UTC epoch time
    r.zadd('user:%d:following' % who_uid, timegm(gmtime()), whom_uid)
    r.zadd('user:%d:followers' % whom_uid, timegm(gmtime()), who_uid)
    return True


def unfollow_user(who_uid, whom_uid):
    """
    Remove whom from whos following set and remove who from whoms followers set
    """
    who_uid = int(who_uid)
    whom_uid = int(whom_uid)
    if r.zrank('user:%d:following' % who_uid, whom_uid) is None:
        return False
    # Delete uid from who following and whom followers
    r.zrem('user:%d:following' % who_uid, whom_uid)
    r.zrem('user:%d:followers' % whom_uid, who_uid)
    return True


def is_following(who_uid, whom_uid):
    """
    Check to see if who is following whom. These need to be uids
    """
    return True if r.zrank("user:%s:following" % who_uid, whom_uid) is not None else False


def search(query, page=1):
    per_page = app.config['PROFILE_ITEMS_PER_PAGE']
    # Clean up query string
    username_re = re.compile('[^a-zA-Z0-9_]+')
    query = username_re.sub('', query)
    # Lets find and get the users
    if len(query) > 0:
        keys = r.keys('uid:username:%s*' % query)
    else:
        keys = []
    results = []
    for key in keys:
        uid = r.get(key)
        results.append(get_user(uid))
    total = len(results)
    return Pagination(results, total, page, per_page)