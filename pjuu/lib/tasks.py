# -*- coding: utf8 -*-

# Copyright 2014 Joe Doherty <joe@pjuu.com>
#
# Pjuu is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Pjuu is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Pjuu imports
from pjuu import redis as r
from pjuu.keys import *


# ALl of these are too be put in to Celery in the future
# These are here and not in there respective modules due to circular imports
# when it comes to the auth module. This whole this needs refactoring.


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
    followers = r.zrange(USER_FOLLOWERS % uid, 0, -1)
    # This is not transactional as to not hold Redis up.
    for fid in followers:
        fid = int(fid)
        r.lpush(USER_FEED % fid, pid)
        # Stop followers feeds from growing to large
        r.ltrim(USER_FEED % fid, 0, 999)

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
        cids = r.lrange(USER_COMMENTS % pid, 0, -1)
    else:
        # Delete all comments made by a user
        cids = r.lrange(USER_COMMENTS % uid, 0, -1)

    for cid in cids:
        cid = int(cid)
        # We need to get the comment authors uid so that we can remove the
        # comment from there user:$uid:comments list
        author_id = r.hget(COMMENT % cid, uid)
        # Delete the comment hash
        r.delete(COMMENT % int(cid))
        # Delete all votes on the comment
        r.delete(COMMENT_VOTES % int(cid))
        # Delete the comment from the users comment list
        r.lrem(USER_COMMENTS % author_id, cid)

    # Delete the correct list after this operation
    if pid is not None:
        r.delete(POST_COMMENTS % pid)
    else:
        r.delete(USER_COMMENTS % pid)

    return True


def delete_posts(uid):
    """
    This function is solely for deleting all posts made by a user
    during account deletion.

    It will iterate over "user:$uid:posts" and remove each one. It will
    also call the delete_comments() function for each post.

    Please be aware this function could take an incredibly long time
    """
    pids = r.lrange(USER_POSTS % uid, 0, -1)

    for pid in pids:
        pid = int(pid)
        # Delete post
        r.delete(POST % pid)
        r.delete(POST_VOTES % pid)
        # Delete the post from the users post list
        r.lrem(USER_POSTS % uid, 0, pid)
        # Get the task to delete all comments on the post
        delete_comments(uid, pid=pid)

    # Delete the users post list after this operation
    r.delete(USER_POSTS % uid)

    return True


def delete_followers(uid):
    """
    This will delete all a users followers and iterate through the list to
    clean the following list of each user
    """
    fids = r.zrange(USER_FOLLOWERS % uid, 0, -1)

    for fid in fids:
        fid = int(fid)
        # Clear the followers following list of the uid
        r.zrem(USER_FOLLOWING % fid, uid)

    # Delete the followers list
    r.delete(USER_FOLLOWERS % uid)

    return True


def delete_following(uid):
    """
    This will delete all a users following list. It will iterate through
    the list and clean the followers list of each user
    """
    fids = r.zrange(USER_FOLLOWING % uid, 0, -1)

    for fid in fids:
        fid = int(fid)
        # Clear the followers list of people uid is following
        r.zrem(USER_FOLLOWERS % fid, uid)

    # Delete the following list
    r.delete(USER_FOLLOWING % uid)

    return True
