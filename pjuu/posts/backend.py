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
    # Add post
    pipe.hmset('post:%d' % pid, post)
    # Add post to users post list
    pipe.lpush('posts:%d' % uid, pid)
    # Add post to authors feed
    pipe.lpush('feed:%d' % uid, pid)
    # Ensure the feed does not grow to large
    pipe.ltrim('feed:%d' % uid, 0, 999)
    pipe.execute()
    # Append to all followers feeds
    # TODO This needs putting in to Celery->RabbitMQ at some point
    # as this could take a long long while.
    followers = r.zrange('followers:%d' % uid, 0, -1)
    # This is not transactional as to not hold Redis up.
    for fid in followers:
        r.lpush('feed:%s' % fid, pid)
        # Stop followerss feed from growing to large
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
    # Add comment
    pipe.hmset('comment:%d' % cid, comment)
    # Add comment to posts comment list
    pipe.rpush('comments:%d' % pid, cid)
    pipe.execute()
    return cid


def check_post(username, pid, cid=None):
    """
    This function will ensure that cid belong to pid and pid
    belongs to username. If post is not a comment then pass
    None should be passed to cid.
    """
    try:
        pid = int(pid)
        if cid:
            cid = int(cid)
            pid_check = int(r.hget('comment:%d' % cid, 'pid'))
            if int(pid_check) != pid:
                return False
        uid = r.get('uid:%s' % username)
        uid_check = r.hget('post:%d' % pid, 'uid')
        if uid_check != uid:
            return False
        return True
    except:
        return False


def get_post(pid):
    """
    Returns a dictionary which has everything to display a Post
    """
    post = r.hgetall('post:%d' % int(pid))
    if post:
        user_dict = r.hgetall('user:%s' % post['uid'])
        post['user_username'] = user_dict['username']
        post['user_email'] = user_dict['email']
        post['user_score'] = user_dict['score']
        post['comment_count'] = r.llen('comments:%d' % int(pid))
    return post


def get_comment(cid):
    """
    Returns a dictionary which has everything to display a Comment
    """
    comment = r.hgetall('comment:%d' % int(cid))
    if comment:
        user_dict = r.hgetall('user:%s' % comment['uid'])
        comment['user_username'] = user_dict['username']
        comment['user_email'] = user_dict['email']
        comment['user_score'] = user_dict['score']
    return comment


def upvote(pid, cid=None):
    pass


def downvote(pid, cid=None):
    pass


def delete(pid, cid=None):
    pass