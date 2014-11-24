# -*- coding: utf-8 -*-

"""
Description:
    The backend function for the post system.

    If in the future we decice to replace Redis we can simply change all these
    funtions to use a new backend

Licence:
    Copyright 2014 Joe Doherty <joe@pjuu.com>

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

# Stdlib imports
import re

# 3rd party imports
from flask import current_app as app, url_for
from jinja2.filters import do_capitalize

# Pjuu imports
from pjuu import mongo as m, redis as r
from pjuu.auth.backend import get_uid_username
from pjuu.lib import keys as K, lua as L, timestamp, get_uuid
from pjuu.lib.alerts import BaseAlert, AlertManager
from pjuu.lib.pagination import Pagination
from pjuu.lib.tasks import make_celery


# Create a celery object for this file
celery = make_celery(app)


# Used to match '@' tags in a post
TAG_RE = re.compile('(?:^|(?<=[^\w]))@'
                    '(\w{3,16})(?:$|(?=[\.\;\,\:\ \t]))')


class CantVoteOnOwn(Exception):
    """Raised when a user tries to vote on a post they authored

    """
    pass


class AlreadyVoted(Exception):
    """Raised when a user tries to vote on a post they have already voted on

    """
    pass


class SubscriptionReasons(object):
    """Constants describing subscriptions to a post

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

    def __init__(self, user_id, post_id):
        # Call the BaseAlert __init__ method
        super(PostingAlert, self).__init__(user_id)
        self.post_id = post_id

    def url(self):
        """Get the user object or the original author for the post.

        Eg. Bob may have tagged you in the post but Brian posted the original
            post. This is needed to generate the URL.

        """
        # Get the author of the posts username so that we can build the URL
        author = m.db.posts.find_one({'_id': self.post_id},
                                     {'username': True, '_id': False})
        # Return the username or None
        return author.get('username')

    def verify(self):
        """Overwrites the verify() of BaseAlert to check the post exists

        """
        return m.db.users.find({'_id': self.user_id}).limit(1) and \
            m.db.posts.find({'_id': self.post_id}).limit(1)


class TaggingAlert(PostingAlert):
    """Form of all tagging alert messages

    """

    def prettify(self, for_uid=None):
        return '<a href="{0}">{1}</a> tagged you in a <a href="{2}">post</a>' \
               .format(url_for('profile', username=self.user.get('username')),
                       do_capitalize(self.user.get('username')), self.url)


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
               .format(url_for('profile', username=self.user.get('username')),
                       do_capitalize(self.user.get('username')), self.url, sr)


def create_post(user_id, username, body, reply_to=None):
    """Creates a new post

    This handled both posts and what used to be called comments. If the
    reply_to field is not None then the post will be treat as a comment.
    You will need to make sure the reply_to post exists.

    :param user_id: The user id of the user posting the post
    :type user_id: str
    :param username: The user name of the user posting (denormalised)
    :type username: str
    :param body: The content of the post
    :type body: str
    :param reply_to: The post id of the post this is a reply to if any
    :type reply_to: str
    :returns: The post id of the new post
    :rtype: str or None

    """
    # Get a new UUID for the post_id ("_id" in MongoDB)
    post_id = get_uuid()

    post = {
        '_id': post_id,             # Newly created post id
        'user_id': user_id,         # User id of the poster
        'username': username,       # Username of the poster
        'body': body,               # Body of the post
        'created': timestamp(),     # Unix timestamp for this moment in time
        'score': 0,                 # Atomic score counter
        'comment_count': 0          # Atomic comment counter (saves db call)
    }

    # If this is a comment on a post then the reply_to parameter will be set
    # add it too the post
    if reply_to is not None:
        post['reply_to'] = reply_to

    # Add the post to the database
    # If the post isn't stored, result will be None
    result = m.db.posts.insert(post)

    # Only carry out the rest of the actions if the insert was successful
    if result:
        # Is this a comment?
        if reply_to is None:
            # Handle what Pjuu < v0.6 called a POST

            # Add post to authors feed
            r.lpush(K.USER_FEED.format(user_id), post_id)
            # Ensure the feed does not grow to large
            r.ltrim(K.USER_FEED.format(user_id), 0, 999)

            # Subscribe the poster to there post
            subscribe(user_id, post_id, SubscriptionReasons.POSTER)

            # TAGGING

            # Create alert manager and alert
            alert = TaggingAlert(user_id, post_id)
            # Alert tagees
            tagees = parse_tags(body)
            # Store a list of uids which need to alerted to the tagging
            tagees_to_alert = []
            for tagee in tagees:
                # Don't allow tagging yourself
                if tagee[0] != user_id:
                    # Subscibe the tagee to the post
                    subscribe(tagee[0], post_id, SubscriptionReasons.TAGEE)
                    # Add the tagee's uid to the list to alert them
                    tagees_to_alert.append(tagee[0])

            # Alert the required tagees
            AlertManager().alert(alert, tagees_to_alert)

            # Append to all followers feeds
            populate_followers_feeds(user_id, post_id)

        else:
            # Handle what Pjuu < v0.6 called a COMMENT

            # To reduce database look ups on the read path we will increment
            # the reply_to's comment count.
            m.db.posts.update({'_id': reply_to},
                              {'$inc': {'comment_count': 1}})

            # COMMENT ALERTING

            # Alert all subscribers to the post that a new comment has been
            # added. We do this before subscribing anyone new
            alert = CommentingAlert(user_id, post_id)

            subscribers = []
            # Iterate through subscribers and let them know about the comment
            for subscriber_id in get_subscribers(post_id):
                # Ensure we don't get alerted for our own comments
                if subscriber_id != user_id:
                    subscribers.append(subscriber_id)

            # Push the comment alert out to all subscribers
            AlertManager().alert(alert, subscribers)

            # Subscribe the user to the post, will not change anything if they
            # are already subscribed
            subscribe(user_id, post_id, SubscriptionReasons.COMMENTER)

            # TAGGING

            # Create alert
            alert = TaggingAlert(user_id, post_id)

            # Subscribe tagees
            tagees = parse_tags(body)
            tagees_to_alert = []
            for tagee in tagees:
                # Don't allow tagging yourself
                if tagee[0] != user_id:
                    subscribe(tagee[0], post_id, SubscriptionReasons.TAGEE)
                    tagees_to_alert.append(tagee[0])

            # Get an alert manager to notify all tagees
            AlertManager().alert(alert, tagees_to_alert)

        # Return the id of the new post
        return post_id

    # If there was a problem putting the post in to Mongo we will return None
    return None


def parse_tags(body, deduplicate=False):
    """Finds '@' tags within a posts body.

    This is used by create_post to alert users that they have been tagged in a
    post and by the 'nameify' template_filter also uses this to identify tags
    before it inserts the links. See nameify_filter() in posts.views

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
        user_id = get_uid_username(tag.group(1))
        if user_id is not None:
            if not deduplicate:
                results.append((user_id, tag.group(1),
                                tag.group(0), tag.span()))
            elif user_id not in seen:
                results.append((user_id, tag.group(1),
                                tag.group(0), tag.span()))
                seen.append(user_id)

    return results


@celery.task
def populate_followers_feeds(user_id, post_id):
    """Fan out a pid to all the users followers.

    This can be run on a worker to speed the process up.

    """
    print "POPULATE_FOLLOWERS_FEEDS"
    # Get a list of ALL users who are following a user
    followers = r.zrange(K.USER_FOLLOWERS.format(user_id), 0, -1)
    # This is not transactional as to not hold Redis up.
    for follower_id in followers:
        # Add the pid to the list
        r.lpush(K.USER_FEED.format(follower_id), post_id)
        # Stop followers feeds from growing to large, doesn't matter if it
        # doesn't exist
        r.ltrim(K.USER_FEED.format(follower_id), 0, 999)


def check_post(user_id, post_id, reply_id=None):
    """Ensure reply_id is a reply_to post_id and that post_id was created by
    user_id.

    WARNING: Think before testing. user_id is the person wrote post_id,
             reply_id if assigned has to have been a reply to post_id.
             This for checking the urls not for checking who wrote reply_id

    """
    # Check if cid is a comment of post pid
    if reply_id:
        # Get the reply_to field of the reply object and check it matches
        reply = m.db.posts.find_one({'_id': reply_id}, {'reply_to': True})
        if reply.get('reply_to') != post_id:
            return False

    # Get the user_id for post with post_id to verify
    post = m.db.posts.find_one({'_id': post_id}, {'user_id': True})
    if post.get('user_id') != user_id:
        return False

    # The post was valid!!!
    return True


def get_post(post_id):
    """Returns a post. Simple helper function

    """
    return m.db.posts.find_one({'_id': post_id})


def get_posts(user_id, page=1):
    """Returns a users posts as a pagination object.

    """
    per_page = app.config.get('PROFILE_ITEMS_PER_PAGE')
    total = m.db.posts.find({'uid': user_id}).count()
    cursor = m.db.comments.find({'uid': user_id}) \
        .sort('created', -1).skip((page - 1) * per_page).limit(per_page)

    posts = []
    for post in cursor:
        posts.append(post)

    return Pagination(posts, total, page, per_page)


def get_replies(post_id, page=1):
    """Returns all a posts comments as a pagination object.

    """
    per_page = app.config.get('PROFILE_ITEMS_PER_PAGE')
    total = m.db.posts.find({'_id': post_id}).count()
    cursor = m.db.posts.find({'reply_to': post_id}) \
        .sort('created', -1).skip((page - 1) * per_page).limit(per_page)

    comments = []
    for comment in cursor:
        comments.append(comment)

    return Pagination(comments, total, page, per_page)


def has_voted(user_id, post_id):
    """Check if a user has voted on a post or a comment, if so return the vote.

    """
    return r.zscore(K.POST_VOTES.format(post_id), user_id)


def vote_post(uid, pid, amount=1):
    """Handles voting on posts

    """
    # Get the comment so we can check who the author is
    author_uid = get_post(pid).get('uid')

    if not has_voted(uid, pid):
        if author_uid != uid:
            r.zadd(K.POST_VOTES.format(pid), amount, uid)
            # Increment the score by amount (can be negative)
            # Post score can go lower than 0
            m.db.posts.update({'_id': pid},
                              {'$inc': {'score': amount}})

            if amount < 0:
                # Don't decrement the users score if it is already at 0
                # we use a query to ONLY find user if the score if greater than
                # 0. This might seem stange but it is in the only way to keep
                # this atomic
                m.db.users.update({'_id': author_uid, 'score': {'$gt': 0}},
                                  {'$inc': {'score': amount}})
            else:
                # If its an increment it doesn't really matter
                m.db.users.update({'_id': author_uid},
                                  {'$inc': {'score': amount}})
        else:
            raise CantVoteOnOwn
    else:
        raise AlreadyVoted


def delete_post(post_id):
    """Deletes a post

    """
    post = get_post(post_id)

    # Delete votes and subscribers from Redis
    r.delete(K.POST_VOTES.format(post.get('_id')))
    if post.get('reply_to'):
        r.delete(K.POST_SUBSCRIBERS.format(post.get('_id')))

    # Delete the post from MongoDB
    m.db.posts.remove({'_id': post_id})

    # Trigger deletion all posts comments if this post isn't a reply
    if not post.get('reply_to'):
        delete_post_replies(post_id)


@celery.task()
def delete_post_replies(post_id):
    """Delete ALL comments on post with pid.

    This can't be done in one single call to Mongo because we need to remove
    the votes from Redis!

    """
    # Get a cursor for all the posts comments
    cur = m.db.comments.find({'post_id': post_id}, {'_id': 1})

    # Iterate over the cursor and call delete comment on each one
    for reply in cur:
        # Delete votes and subscribers from Redis
        r.delete(K.POST_VOTES.format(reply.get('_id')))

        # Delete the comment itself from MongoDB
        m.db.posts.remove({'_id': post_id})


def subscribe(user_id, post_id, reason):
    """Subscribes a user (uid) to post (pid) for reason.

    """
    # Check that pid exsits if not do nothing
    if not m.db.posts.find_one({'_id': post_id}, {}):
        return False

    # Only subscribe the user if the user is not already subscribed
    # this will mean the original reason is kept
    return L.zadd_member_nx(keys=[K.POST_SUBSCRIBERS.format(post_id)],
                            args=[reason, user_id])


def unsubscribe(user_id, post_id):
    """Unsubscribe a user from a post.

    """
    # Actually remove the uid from the subscribers list
    return bool(r.zrem(K.POST_SUBSCRIBERS.format(post_id), user_id))


def get_subscribers(post_id):
    """Return a list of subscribers for a given post

    """
    return r.zrange(K.POST_SUBSCRIBERS.format(post_id), 0, -1)


def is_subscribed(user_id, post_id):
    """Returns a boolean to denote if a user is subscribed or not

    """
    return r.zrank(K.POST_SUBSCRIBERS.format(post_id), user_id) is not None


def subscription_reason(user_id, post_id):
    """Returns the reason a user is subscribed to a post.

    """
    return r.zscore(K.POST_SUBSCRIBERS.format(post_id), user_id)
