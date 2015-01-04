# -*- coding: utf-8 -*-

"""
Description:
    The backend function for the post system.

    If in the future we decice to replace Redis we can simply change all these
    funtions to use a new backend

Licence:
    Copyright 2014-2015 Joe Doherty <joe@pjuu.com>

    Pjuu is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    Pjuu is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

# Stdlib
import re
# 3rd party imports
from flask import current_app as app, url_for
from jinja2.filters import do_capitalize
# Pjuu imports
from pjuu import redis as r
from pjuu.auth.backend import get_uid_username, get_username
from pjuu.lib import keys as K, lua as L, timestamp, get_uuid
from pjuu.lib.alerts import BaseAlert, AlertManager


# Used to match '@' tags in a post
TAG_RE = re.compile('(?:^|(?<=[^\w]))@'
                    '(\w{3,16})(?:$|(?=[\.\;\,\:\ \t]))')


class CantVoteOnOwn(Exception):
    """Raised when a user tries to vote on a post or comment they authored

    """
    pass


class AlreadyVoted(Exception):
    """Raised when a user tries to vote on a post or comment they have already
    voted on

    """
    pass


class SubscriptionReasons(object):
    """Constants describing subscriptions to post

    """
    # You are the original poster
    POSTER = 1
    # You commented on the post
    COMMENTER = 2
    # You have been tagged in the post
    TAGEE = 3


class PostingAlert(BaseAlert):
    """Base form for all alerts used within the posts package.

    """

    def __init__(self, uid, pid):
        # Call the BaseAlert __init__ method
        super(PostingAlert, self).__init__(uid)
        self.pid = pid
        self.author_uid = r.hget(K.POST.format(pid), 'uid')

    def author_username(self):
        """Get the username of the user which triggered this alert

        """
        return r.hget(K.USER.format(self.author_uid), 'username')

    def verify(self):
        """ Overwrites the verify() of BaseAlert to check the post exists

        """
        return r.exists(K.USER.format(self.uid)) and \
            r.exists(K.POST.format(self.pid))


class TaggingAlert(PostingAlert):
    """Form of all tagging alert messages

    """

    def prettify(self, for_uid=None):
        return '<a href="{0}">{1}</a> tagged you in a <a href="{2}">post</a>' \
               .format(url_for('profile', username=self.get_username()),
                       do_capitalize(self.get_username()),
                       url_for('view_post', username=self.author_username(),
                               pid=self.pid))


class CommentingAlert(PostingAlert):
    """Form of all commenting alert messages

    """

    def prettify(self, for_uid):
        # Let's try and work out why this user is being notified of a comment
        reason = subscription_reason(for_uid, self.pid)

        if reason == SubscriptionReasons.POSTER:
            sr = 'posted'
        elif reason == SubscriptionReasons.COMMENTER:
            sr = 'commented on'
        elif reason == SubscriptionReasons.TAGEE:
            sr = 'were tagged in'
        else:
            # This should never really happen but let's play ball eh?
            sr = 'are subscribed too'

        return '<a href="{0}">{1}</a> ' \
               'commented on a <a href="{2}">post</a> you {3}' \
               .format(url_for('profile', username=self.get_username()),
                       do_capitalize(self.get_username()),
                       url_for('view_post', username=self.author_username(),
                               pid=self.pid),
                       sr)


def create_post(uid, body):
    """Creates a new post

    """
    # Get a new UUID for the pid
    pid = get_uuid()

    # Hash form for posts
    # TODO this needs expanding to include some form of image upload hook
    post = {
        'pid': pid,
        'uid': uid,
        'body': body,
        'created': timestamp(),
        'score': 0
    }

    # Add post
    r.hmset(K.POST.format(pid), post)
    # Add post to users post list
    r.lpush(K.USER_POSTS.format(uid), pid)
    # Add post to authors feed
    r.lpush(K.USER_FEED.format(uid), pid)
    # Ensure the feed does not grow to large
    r.ltrim(K.USER_FEED.format(uid), 0, 999)

    # Append to all followers feeds
    populate_feeds(uid, pid)

    # Subscribe the poster to there post
    subscribe(uid, pid, SubscriptionReasons.POSTER)

    # TAGGING

    # Create alert manager and alert
    alert = TaggingAlert(uid, pid)
    # Alert tagees
    tagees = parse_tags(body)
    # Store a list of uids which need to alerted to the tagging
    tagees_to_alert = []
    for tagee in tagees:
        # Don't allow tagging yourself
        if tagee[0] != uid:
            # Subscribe the tagee to the alert
            subscribe(tagee[0], pid, SubscriptionReasons.TAGEE)
            # Add the tagee's uid to the list to alert them
            tagees_to_alert.append(tagee[0])

    # Alert the required tagees
    AlertManager().alert(alert, tagees_to_alert)

    return pid


def create_comment(uid, pid, body):
    """Create a new comment

    """
    # Get a new UUID for the cid
    cid = get_uuid()

    # Form for comment hash
    comment = {
        'cid': cid,
        'uid': uid,
        'pid': pid,
        'body': body,
        'created': timestamp(),
        'score': 0
    }

    # Add comment
    r.hmset(K.COMMENT.format(cid), comment)
    # Add comment to posts comment list
    r.lpush(K.POST_COMMENTS.format(pid), cid)
    # Add comment to users comment list
    # This may seem redundant but it allows for perfect account deletion
    # Please see Issue #3 on Github
    r.lpush(K.USER_COMMENTS.format(uid), cid)

    # COMMENT ALERTING

    # Alert all subscribers to the post that a new comment has been added.
    # We do this before subscribing anyone new
    # Create alert manager and alert
    alert = CommentingAlert(uid, pid)

    subscribers = []
    # Iterate through subscribers and let them know about the comment
    for subscriber in get_subscribers(pid):
        # Ensure we don't get alerted for our own comments
        if subscriber != uid:
            subscribers.append(subscriber)

    # Push the comment alert out to all subscribers
    AlertManager().alert(alert, subscribers)

    # Subscribe the user to the post, will not change anything if they are
    # already subscribed
    subscribe(uid, pid, SubscriptionReasons.COMMENTER)

    # TAGGING

    # Create alert
    alert = TaggingAlert(uid, pid)

    # Subscribe tagees
    tagees = parse_tags(body)
    tagees_to_alert = []
    for tagee in tagees:
        # Don't allow tagging yourself
        if tagee[0] != uid:
            subscribe(tagee[0], pid, SubscriptionReasons.TAGEE)
            tagees_to_alert.append(tagee[0])

    # Get an alert manager to notify all tagees
    AlertManager().alert(alert, tagees_to_alert)

    return cid


def parse_tags(body, deduplicate=False):
    """Find '@' tags within a posts or comments body.

    This is used by create_post and create_comment to alert users
    that they have been tagged in a post.

    The 'nameify' template_filter also uses this to identify tags before it
    inserts the links. See nameify_filter() in posts.views

    This returns a list of tuples (uid, username, tag, span)

    'deduplicate' remove duplicate instances of a tag. Used by the alerting
                  system to only send one alert to a user even if someone
                  repeats the tag. Having this as false allows us to highlight
                  all the tags in the nameify_filter
    """
    tags = TAG_RE.finditer(body)

    results = []
    seen = []

    for tag in tags:
        # Check the tag is of an actual user
        uid = get_uid_username(tag.group(1))
        if uid is not None:
            if deduplicate:
                results.append((uid, tag.group(1), tag.group(0), tag.span()))
            elif uid not in seen:
                results.append((uid, tag.group(1), tag.group(0), tag.span()))
                seen.append(uid)

    return results


# TODO: Hungry Otter
def populate_feeds(uid, pid):
    """Fan out a pid to all the users with uid's followers

    """
    # Get a list of ALL users who are following a user
    followers = r.zrange(K.USER_FOLLOWERS.format(uid), 0, -1)
    # This is not transactional as to not hold Redis up.
    for fid in followers:
        # Add the pid to the list
        r.lpush(K.USER_FEED.format(fid), pid)
        # Stop followers feeds from growing to large, doesn't matter if it
        # doesn't exist
        r.ltrim(K.USER_FEED.format(fid), 0, 999)


def check_post(uid, pid, cid=None):
    """Ensure cid is related pid is related to uid

    Warning: Think before testing. UID is the person wrote PID, CID if assigned
             has to be a comment of PID. This for checking the urls not for
             checking who wrote CID
    """
    # Check if cid is a comment of post pid
    if cid:
        pid_check = r.hget(K.COMMENT.format(cid), 'pid')

        if pid_check is None or pid_check != pid:
            # No it isn't
            return False

    # Check that post was written by uid
    uid_check = r.hget(K.POST.format(pid), 'uid')
    if uid_check is None or uid_check != uid:
        return False

    # All was good
    return True


def get_post(pid):
    """Returns a representation of a post along with data on the user

    """
    post = r.hgetall(K.POST.format(pid))

    if post:
        # Look up user and add data to the repr
        user = r.hgetall(K.USER.format(post.get('uid')))

        # This should never happen unless something really really bad has
        # happen
        if user is not None:  # pragma: no branch
            post['user_username'] = user.get('username')
            post['user_email'] = user.get('email')
            post['user_score'] = user.get('score')
            post['comment_count'] = r.llen(K.POST_COMMENTS.format(pid))
            return post

    # We never got a post or never got a user
    return None


def get_comment(cid):
    """Returns a representation of a comment along with data on the user

    """
    comment = r.hgetall(K.COMMENT.format(cid))

    if comment:
        # Look up user and add data to the repr
        user = r.hgetall(K.USER.format(comment.get('uid')))

        # This should never happen unless something really really bad has
        # happen
        if user is not None:  # pragma: no branch
            comment['user_username'] = user.get('username')
            comment['user_email'] = user.get('email')
            comment['user_score'] = user.get('score')

            # We need the username from the parent pid to construct a URL
            # Get the uid from the post
            post_author_uid = \
                r.hget(K.POST.format(comment.get('pid')), 'uid')
            # Look up the uid for the username
            comment['post_author'] = get_username(post_author_uid)

            # This should also not happen it is a worst-case scenario.
            if comment.get('post_author') is not None:  # pragma: no branch
                # Only return the comment if we got all the data we needed
                return comment

    # We never got a comment or never got a user
    return None


def get_post_author(pid):
    """Returns uid of posts author

    """
    return r.hget(K.POST.format(pid), 'uid')


def get_comment_author(cid):
    """Returns UID of comments author

    """
    return r.hget(K.COMMENT.format(cid), 'uid')


def has_voted(uid, xid, comment=False):
    """Check if a user has voted on a post or a comment, if so return the vote.

    'xid' can be either a pid or a cid. If it is a cid, the comment flag needs
          to be set too True.

    """
    if comment:
        result = r.zscore(K.COMMENT_VOTES.format(xid), uid)
    else:
        result = r.zscore(K.POST_VOTES.format(xid), uid)
    return result


def vote_post(uid, pid, amount=1):
    """Handles voting on posts

    """
    # Ensure user has not voted before
    if not has_voted(uid, pid):
        author_uid = get_post_author(pid)
        if author_uid != uid:
            r.zadd(K.POST_VOTES.format(pid), amount, uid)
            # Post scores can be negative.
            # INCRBY with a minus value is the same a DECRBY
            r.hincrby(K.POST.format(pid), 'score', amount=amount)

            # Get the score of the author
            cur_user_score = r.hget(K.USER.format(author_uid), 'score')
            # Stop users scores going lower than 0
            cur_user_score = int(cur_user_score)
            if cur_user_score <= 0 and amount < 0:
                amount = 0

            # Increment the users score
            r.hincrby(K.USER.format(author_uid), 'score', amount=amount)
        else:
            raise CantVoteOnOwn
    else:
        raise AlreadyVoted


def vote_comment(uid, cid, amount=1):
    """Handles voting on posts

    """
    # Ensure user has not voted before and ensure its a comment check
    if not has_voted(uid, cid, comment=True):
        author_uid = get_comment_author(cid)
        if author_uid != uid:
            r.zadd(K.COMMENT_VOTES.format(cid), amount, uid)
            # Post scores can be negative.
            # INCRBY with a minus value is the same a DECRBY
            r.hincrby(K.COMMENT.format(cid), 'score', amount=amount)

            # Get the score of the author
            cur_user_score = r.hget(K.USER.format(author_uid), 'score')
            # Stop users scores going lower than 0
            cur_user_score = int(cur_user_score)
            if cur_user_score <= 0 and amount < 0:
                amount = 0

            # Increment the users score
            r.hincrby(K.USER.format(author_uid), 'score', amount=amount)
        else:
            raise CantVoteOnOwn
    else:
        raise AlreadyVoted


def delete_post(pid):
    """Deletes a post

    """
    # Get the post authors uid
    uid = r.hget(K.POST.format(pid), 'uid')

    # Delete post, votes and subscribers
    r.delete(K.POST.format(pid))
    r.delete(K.POST_VOTES.format(pid))
    r.delete(K.POST_SUBSCRIBERS.format(pid))

    # Delete the post from the users post list
    r.lrem(K.USER_POSTS.format(uid), 0, pid)

    # Trigger deletion all posts comments
    delete_post_comments(pid)


def delete_comment(cid):
    """Delete a comment.

    """
    # Get the comment authors uid and the parents post pid
    [uid, pid] = r.hmget(K.COMMENT.format(cid), 'uid', 'pid')

    # Delete comment and votes
    r.delete(K.COMMENT.format(cid))
    r.delete(K.COMMENT_VOTES.format(cid))

    # Delete the comment from the users comment list
    r.lrem(K.USER_COMMENTS.format(uid), 0, cid)
    # Delete the comment from the posts comment list
    r.lrem(K.POST_COMMENTS.format(pid), 0, cid)


# TODO: Hungry Otter
def delete_post_comments(pid):
    """Delete ALL comments on post with pid

    """
    # Get a list of all cids on the post
    cids = r.lrange(K.POST_COMMENTS.format(pid), 0, -1)

    for cid in cids:
        # Make a call to delete comment
        delete_comment(cid)

    # Finally delete the comment list. It should already be gone as there will
    # be nothing left within it. We are just being careful.
    r.delete(K.POST_COMMENTS.format(pid))


def subscribe(uid, pid, reason):
    """Subscribes a user (uid) to post (pid) for reason.

    """
    # Check that pid exsits if not do nothing
    if not r.exists(K.POST.format(pid)):
        return False

    # Only subscribe the user if the user is not already subscribed
    # this will mean the original reason is kept
    return L.zadd_member_nx(keys=[K.POST_SUBSCRIBERS.format(pid)],
                            args=[reason, uid])


def unsubscribe(uid, pid):
    """Unsubscribe a user from a post.

    """
    # Actually remove the uid from the subscribers list
    return bool(r.zrem(K.POST_SUBSCRIBERS.format(pid), uid))


def get_subscribers(pid):
    """Return a list of subscribers for a given post

    """
    return r.zrange(K.POST_SUBSCRIBERS.format(pid), 0, -1)


def is_subscribed(uid, pid):
    """Returns a boolean to denote if a user is subscribed or not

    """
    return r.zrank(K.POST_SUBSCRIBERS.format(pid), uid) is not None


def subscription_reason(uid, pid):
    """Returns the reason a user is subscribed to a post.

    """
    return r.zscore(K.POST_SUBSCRIBERS.format(pid), uid)
