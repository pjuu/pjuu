# -*- coding: utf-8 -*-

##############################################################################
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
##############################################################################

# Stdlib
import re
# Pjuu imports
from pjuu import app, keys as K, lua as L, redis as r
from pjuu.lib import timestamp
from pjuu.auth.backend import get_uid_username


# Regular expressions
# Used to match '@' tags in a post
tag_re = re.compile('(?:^|(?<=[^\w]))@'
                    '(\w{3,16})(?:$|(?=[\.\;\,\:\ \t]))')


def parse_tags(body, send_all=False):
    """
    This function looks for '@' tags inside a post that match the regex.

    This is used by create_post and create_comment to alert users
    that they have been tagged in a post.

    The 'nameify' template_filter also uses this to identify tags before it
    inserts the links. See nameify_filter() in posts/views.py

    This returns a list of tuples (uid, username, tag, span)

    'send_all' allows the tag highlighting in nameify() to highlight
    all tags. This is not needed for alerts as someone can only subscribe
    once
    """
    tags = tag_re.finditer(body)

    results = []
    seen = []

    for tag in tags:
        # Check the tag is of an actual user
        uid = get_uid_username(tag.group(1))
        if uid is not None:
            # There is two versions one sends all tag locations and the other
            # deduplicates the list.
            if send_all:
                results.append((uid, tag.group(1), tag.group(0), tag.span()))
            elif uid not in seen:
                results.append((uid, tag.group(1), tag.group(0), tag.span()))
                seen.append(uid)

    return results


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
    followers = r.zrange(K.USER_FOLLOWERS % uid, 0, -1)
    # This is not transactional as to not hold Redis up.
    for fid in followers:
        fid = int(fid)
        # >> LUA
        r.lpush(K.USER_FEED % fid, pid)
        # Stop followers feeds from growing to large, doesn't matter if it
        # doesn't exist
        r.ltrim(K.USER_FEED % fid, 0, 999)


def create_post(uid, body):
    """
    Creates a new post. Does all the other stuff to like prepend to feeds,
    post list, etc...
    """
    uid = int(uid)
    pid = int(r.incr(K.GLOBAL_PID))
    # Hash form for posts
    # TODO this needs expanding to include some form of image upload hook
    post = {
        'pid': pid,
        'uid': uid,
        'body': body,
        'created': timestamp(),
        'score': 0
    }
    # Transactional
    pipe = r.pipeline()
    # Add post
    pipe.hmset(K.POST % pid, post)
    # Add post to users post list
    pipe.lpush(K.USER_POSTS % uid, pid)
    # Add post to authors feed
    pipe.lpush(K.USER_FEED % uid, pid)
    # Ensure the feed does not grow to large
    pipe.ltrim(K.USER_FEED % uid, 0, 999)
    pipe.execute()
    # Append to all followers feeds
    populate_feeds(uid, pid)

    return pid


def create_comment(uid, pid, body):
    """
    Create a new comment.
    """
    uid = int(uid)
    # Reserve the ID now. If the transaction fails we lost this ID
    cid = int(r.incr(K.GLOBAL_CID))
    pid = int(pid)
    # Form for comment hash
    comment = {
        'cid': cid,
        'uid': uid,
        'pid': pid,
        'body': body,
        'created': timestamp(),
        'score': 0
    }
    # Transactional
    pipe = r.pipeline()
    # Add comment
    pipe.hmset(K.COMMENT % cid, comment)
    # Add comment to posts comment list
    pipe.lpush(K.POST_COMMENTS % pid, cid)
    # Add comment to users comment list
    # This may seem redundant but it allows for perfect account deletion
    # Please see Issue #3 on Github
    pipe.lpush(K.USER_COMMENTS % uid, cid)
    pipe.execute()

    return cid


def check_post(uid, pid, cid=None):
    """
    This function will ensure that cid belongs to pid and pid belongs to uid.

    This function would not really be needed if we used a RDBMS but we have
    to manually check this
    """
    try:
        uid = int(uid)
        pid = int(pid)

        # Check if cid is a comment of post pid
        if cid:
            cid = int(cid)
            pid_check = int(r.hget(K.COMMENT % cid, 'pid'))

            if int(pid_check) != pid:
                # No it isn't
                return False

        # Check that post was written by uid
        uid_check = int(r.hget(K.POST % pid, 'uid'))
        if uid_check != uid:
            return False

        # All was good
        return True

    except (TypeError, ValueError):
        # Something went wrong
        return False


def get_post(pid):
    """
    Returns a representation of a post along with data on the user
    """
    pid = int(pid)
    post = r.hgetall(K.POST % pid)

    if post:
        try:
            # Look up user and add data to the repr
            uid = int(post['uid'])
            user_dict = r.hgetall(K.USER % uid)

            post['user_username'] = user_dict['username']
            post['user_email'] = user_dict['email']
            post['user_score'] = user_dict['score']
            post['comment_count'] = r.llen(K.POST_COMMENTS % pid)
        except (KeyError, ValueError):
            return None
        return post
    # We never got a post
    return None


def get_comment(cid):
    """
    Returns a representation of a comment along with data on the user
    """
    cid = int(cid)
    comment = r.hgetall(K.COMMENT % cid)

    if comment:
        try:
            # Look up user and add data to the repr
            uid = int(comment['uid'])
            user_dict = r.hgetall(K.USER % uid)

            comment['user_username'] = user_dict['username']
            comment['user_email'] = user_dict['email']
            comment['user_score'] = user_dict['score']

            # We need the username from the parent pid to construct a URL
            pid = int(comment['pid'])
            author_uid = int(r.hget(K.POST % pid, 'uid'))
            comment['post_author'] = r.hget(K.USER % author_uid, 'username')
        except (KeyError, ValueError):
            return None
        return comment
    # We never got a comment
    return None


def get_post_author(pid):
    """
    Returns UID of posts author
    """
    pid = int(pid)
    return int(r.hget(K.POST % pid, 'uid'))


def get_comment_author(cid):
    """
    Returns UID of comments author
    """
    cid = int(cid)
    return int(r.hget(K.COMMENT % cid, 'uid'))


def has_voted(uid, pid, cid=None):
    """
    Checks to see if uid has voted on a post.

    With return -1 if user downvoted, 1 if user upvoted and None if not voted
    """
    uid = int(uid)
    pid = int(pid)
    if cid is not None:
        cid = int(cid)
        result = r.zscore(K.COMMENT_VOTES % cid, uid)
    else:
        result = r.zscore(K.POST_VOTES % pid, uid)
    return result


def vote(uid, pid, cid=None, amount=1):
    """
    Handles all voting in Pjuu
    """
    uid = int(uid)
    pid = int(pid)

    # If voting on a comment
    if cid is not None:
        cid = int(cid)
        author_uid = int(r.hget(K.COMMENT % cid, 'uid'))
        if author_uid != uid:
            r.zadd(K.COMMENT_VOTES % cid, amount, uid)
            r.hincrby(K.COMMENT % cid, 'score', amount=amount)
            r.hincrby(K.USER % author_uid, 'score', amount=amount)
            return True
    else:
        author_uid = int(r.hget(K.POST % pid, 'uid'))
        if author_uid != uid:
            r.zadd(K.POST_VOTES % pid, amount, uid)
            r.hincrby(K.POST % pid, 'score', amount=amount)
            r.hincrby(K.USER % author_uid, 'score', amount=amount)
            return True

    return False


def delete_comments(uid, pid):
    """
    This will cycle through a posts comments and remove each comment
    in turn.

    It will then delete the list at the end.
    """
    uid = int(uid)
    pid = int(pid)

    cids = r.lrange(K.POST_COMMETNS % pid, 0, -1)
    for cid in cids:
        # Delete comment and votes
        cid = int(cid)
        # We need to get the comment authors uid so that we can remove the
        # comment from there user:$uid:comments list
        author_id = r.hget('comment:%d' % cid, 'uid')
        # Delete the comment and remove from the posts list
        r.delete(K.COMMENT % cid)
        r.delete(K.COMMENT_VOTES % cid)
        # Delete the comment from the users comment list
        # This makes these lists self cleaning
        r.lrem(K.USER_COMMENTS % author_id, 0, cid)
    # Finally delete the comment list
    r.delet(K.POST_COMMENTS % pid)



def delete(uid, pid, cid=None):
    """
    Deletes a post/comment
    If this is a post it will delete all comments, all votes, etc...
    If this is a comment it will delete just this comment and its votes.
    This should not cause users to lose or gain points!

    Please ensure the user has permission to delete the item before
    passing to this, it will not check!
    """
    uid = int(uid)
    pid = int(pid)
    if cid:
        # Delete comment and votes
        cid = int(cid)
        # We need to get the comment authors uid so that we can remove the
        # comment from there user:$uid:comments list
        author_id = r.hget(K.COMMENT % cid, 'uid')
        # Delete the comment and remove from the posts list
        r.delete(K.COMMENT % cid)
        r.delete(K.COMMENT_VOTES % cid)
        r.lrem(K.POST_COMMENTS % pid, 0, cid)
        # Delete the comment from the users comment list
        r.lrem(K.USER_COMMENTS % author_id, 0, cid)
    else:
        # Delete post, comments and votes
        r.delete(K.POST % pid)
        r.delete(K.POST_VOTES % pid)
        # Delete the post from the users post list
        r.lrem(K.USER_POSTS % uid, 0, pid)
        # Delete all comments on the post
        delete_comments(uid, pid)
