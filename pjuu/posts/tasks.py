# -*- coding: utf8 -*-
# Pjuu imports
from pjuu import redis as r


def populate_feeds(uid, pid):
    """
    This will cycle through all a users followers and append the pid to the
    left of their list.
    This will take care of getting the followers from Redis also.
    """
    # TODO This needs putting in to Celery->RabbitMQ at some point
    # as this could take a long long while.
    # This has been seperated in to tasks.py ready for this action.

    # Get a list of ALL users who are following a user
    followers = r.zrange('user:%d:followers' % uid, 0, -1)
    # This is not transactional as to not hold Redis up.
    for fid in followers:
        fid = int(fid)
        r.lpush('user:%d:feed' % fid, pid)
        # Stop followers feeds from growing to large
        r.ltrim('user:%d:feed' % fid, 0, 999)

    # I like return values
    return True


def delete_comments(uid, pid=None):
    """
    This handles deleting comments on Pjuu from a list.
    The list could be the list of all users comments or could be
    all the comments attached to a post.

    The uid always needs to be passed in even though it may not be used.

    If you provide a pid this action will delete all comments on a post.
    If you do not it will delete all posts created by the user
    """
    # This bit may need to go in Celery->RabbitMQ
    if pid is not None:
        # Delete all comments on a post
        cids = r.lrange('post:%d:comments' % pid, 0, -1)
    else:
        # Delete all comments made by a user
        cids = r.lrange('user:%d:comments' % uid, 0, -1)

    for cid in cids:
        # Delete the comment hash
        r.delete('comment:%d' % int(cid))
        # Delete all votes on the comment
        r.delete('comment:%d:votes' % int(cid))

    # Delete the comment list after we have cleaned it
    r.delete('post:%d:comments' % pid)

    return True


def delete_posts(uid):
    """
    This function is solely for deleting all posts made by a user
    during account deletion.

    It will iterate over "user:$uid:posts" and remove each one. It will
    also call the delete_comments() function for each post.

    Please be aware this function could take an incredibly long time!
    """
    pids = r.lrange('user:%d:posts' % uid, 0, -1)

    for pid in pids:
        # Delete post
        r.delete('post:%d' % pid)
        r.delete('post:%d:votes' % pid)
        # Delete the post from the users post list
        r.lrem('user:%d:posts' % uid, 0, pid)
        # Get the task to delete all comments on the post
        delete_comments(uid, pid=pid)

    return True