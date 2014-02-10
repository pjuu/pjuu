# -*- coding: utf-8 -*-

# Stdlib
from time import gmtime
from calendar import timegm
# Pjuu imports
from pjuu import redis as r


def create_post(uid, body):
    """
    Creates a new post. Does all the other stuff to like prepend to feeds,
    post list, etc...
    """
    uid = int(uid)
    pid = int(r.incr('global:pid'))
    # Hash form for posts
    # TODO this needs expanding to include some form of image upload hook
    post = {
        'pid': pid,
        'uid': uid,
        'body': body,
        'created': timegm(gmtime()),
        'score': 0
    }
    # Transactional
    pipe = r.pipeline()
    pipe.hmset('post:%d' % pid, post)
    pipe.lpush('posts:%d' % uid, pid)
    pipe.lpush('feed:%d' % uid, pid)
    pipe.ltrim('feed:%d' % uid, 0, 999)
    pipe.execute()
    # Append to all followers feeds
    # TODO This needs putting in to Celery at some point as this could
    # take a long long while.
    followers = r.smembers('followers:%d' % uid)
    # This is not transactional as to not hold Redis up.
    for fid in followers:
        r.lpush('feed:%s' % fid, pid)
        # This stops the feed from growing to large
        r.ltrim('feed:%s' % fid, 0, 999)
    return pid


def create_comment(uid, pid, body):
    """
    Create a new comment.
    """
    cid = int(r.incr('global:cid'))
    # Form for comment hash
    comment = {
        'cid': cid,
        'uid': uid,
        'pid': pid,
        'body': body,
        'created': timegm(gmtime()),
        'score': 0
    }
    # Transactional
    pipe = r.pipeline()
    pipe.hmset('comment:%d' % cid, comment)
    pipe.rpush('comments:%d' % pid, cid)
    pipe.execute()
    return cid


def get_post(pid):
    """
    Returns a dictionary which has everything to display a Post
    TODO There may be a way to optimise this with less calls to Redis
    """
    post = r.hgetall('post:%d' % int(pid))
    if post:
        post['user_username'] = r.hget('user:%s' % post['uid'], 'username')
        post['user_email'] = r.hget('user:%s' % post['uid'], 'email')
        post['user_score'] = r.hget('user:%s' % post['uid'], 'score')
        post['comment_count'] = r.llen('comments:%d' % int(pid))
    # Do not return and object if we didn't get one
    return post if post else None


def get_comment(cid):
    """
    Returns a dictionary which has everything to display a Comment
    TODO There may be a way to optimise this with less calls to Redis???
    """
    comment = r.hgetall('comment:%d' % cid)
    if comment:
        comment['user_username'] = r.hget('user:%s' % comment['uid'], 'username')
        comment['user_email'] = r.hget('user:%s' % comment['uid'], 'email')
        comment['user_score'] = r.hget('user:%s' % comment['uid'], 'score')
    # Do not return an object if we didn't get one
    return comment if comment else None