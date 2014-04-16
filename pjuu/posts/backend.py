# -*- coding: utf-8 -*-
# Stdlib
from time import gmtime
from calendar import timegm
# Pjuu imports
from pjuu import app, redis as r
from .tasks import populate_feeds, delete_comments


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
    pipe.lpush('user:%d:posts' % uid, pid)
    # Add post to authors feed
    pipe.lpush('user:%d:feed' % uid, pid)
    # Ensure the feed does not grow to large
    pipe.ltrim('user:%d:feed' % uid, 0, 999)
    pipe.execute()
    # Append to all followers feeds
    populate_feeds(uid, pid)

    return pid


def create_comment(uid, pid, body):
    """
    Create a new comment.
    """
    uid = int(uid)
    cid = int(r.incr('global:cid'))
    pid = int(pid)
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
    pipe.lpush('post:%d:comments' % pid, cid)
    # Add comment to users comment list
    # This may seem redundant but it allows for perfect account deletion
    # Please see Issue #3 on Github
    pipe.lpush('user:%d:comments' % uid, cid)
    pipe.execute()
    return cid


def check_post(uid, pid, cid=None):
    """
    This function will ensure that cid belongs to pid and pid belongs to uid
    """
    try:
        pid = int(pid)
        if cid:
            cid = int(cid)
            pid_check = int(r.hget('comment:%d' % cid, 'pid'))
            if int(pid_check) != pid:
                return False
        uid = int(uid)
        uid_check = r.hget('post:%d' % pid, 'uid')
        if int(uid_check) != uid:
            return False
        return True
    except ValueError:
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
        post['comment_count'] = r.llen('post:%d:comments' % int(pid))
    return post


def get_comment(cid):
    """
    This is the in-app representation of a comment.
    """
    comment = r.hgetall('comment:%d' % int(cid))
    if comment:
        user_dict = r.hgetall('user:%s' % comment['uid'])
        comment['user_username'] = user_dict['username']
        comment['user_email'] = user_dict['email']
        comment['user_score'] = user_dict['score']
        # We need the username from the parent pid to construct a URL
        post_author_uid = r.hget('post:%s' % comment['pid'], 'uid')
        comment['post_author'] = r.hget('user:%s' % post_author_uid, 'username')
    return comment


def get_post_author(pid):
    """
    Returns UID of posts author
    """
    return int(r.hget('post:%d' % int(pid), 'uid'))


def get_comment_author(cid):
    """
    Returns UID of comments author
    """
    return int(r.hget('comment:%d' % int(cid), 'uid'))


def has_voted(uid, pid, cid=None):
    """
    Checks to see if uid has voted on a post.
    With return -1 if user downvoted, 1 if user upvoted and None if not voted
    """
    uid = int(uid)
    pid = int(pid)
    if cid is not None:
        cid = int(cid)
        result = r.zscore('comment:%d:votes' % cid, uid)
    else:
        result = r.zscore('post:%d:votes' % pid, uid)
    return result


def vote(uid, pid, cid=None, amount=1):
    """
    Handles all voting in Pjuu
    """
    uid = int(uid)
    pid = int(pid)
    if cid is not None:
        cid = int(cid)
        author_uid = int(r.hget('comment:%d' % cid, 'uid'))
        if author_uid != uid:
            r.zadd('comment:%d:votes' % cid, amount, uid)
            r.hincrby('comment:%d' % cid, 'score', amount=amount)
            r.hincrby('user:%d' % author_uid, 'score', amount=amount)
            return True
    else:
        author_uid = int(r.hget('post:%d' % pid, 'uid'))
        if author_uid != uid:
            r.zadd('post:%d:votes' % pid, amount, uid)
            r.hincrby('post:%d' % pid, 'score', amount=amount)
            r.hincrby('user:%d' % author_uid, 'score', amount=amount)
            return True
    return False


def delete(uid, pid, cid=None):
    """
    Deletes a post/comment
    If this is a post it will delete all comments, all votes, etc...
    If this is a comment it will delete just this comment and its votes.
    This should not cause users to lose or gain points!

    Please ensure the user can delete the item before passing to this
    """
    uid = int(uid)
    pid = int(pid)
    if cid:
        # Delete comment and votes
        cid = int(cid)
        r.delete('comment:%d' % cid)
        r.delete('comment:%d:votes' % cid)
        r.lrem('post:%d:comments' % pid, 0, cid)
    else:
        # Delete post, comments and votes
        r.delete('post:%d' % pid)
        r.delete('post:%d:votes' % pid)
        # Delete the post from the users post list
        r.lrem('user:%d:posts' % uid, 0, pid)
        # Get the task to delete all comments on the post
        delete_comments(uid, pid=pid)
    return True