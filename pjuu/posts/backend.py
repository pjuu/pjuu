# -*- coding: utf-8 -*-

"""Simple functions for dealing with posts, replies, votes and subscriptions
within Redis and MongoDB

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2015 Joe Doherty

"""

# Stdlib imports
import re

# 3rd party imports
from flask import current_app as app, url_for
from jinja2.filters import do_capitalize

# Pjuu imports
from pjuu import mongo as m, redis as r
from pjuu.auth.utils import get_uid_username
from pjuu.lib import keys as k, timestamp, get_uuid
from pjuu.lib.alerts import BaseAlert, AlertManager
from pjuu.lib.lua import zadd_member_nx
from pjuu.lib.pagination import Pagination
from pjuu.lib.uploads import process_upload, delete_upload


# Allow chaning the maximum length of a post
MAX_POST_LENGTH = 500

# Used to match '@' tags in a post
TAG_RE = re.compile(
    r'(?:^|(?<=[.;,:?\(\[\{ \t]))@(\w{3,16})(?:$|(?=[.;,:?\)\]\} \t]))'
)


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
        return url_for('posts.view_post', username=author.get('username'),
                       post_id=self.post_id)

    def verify(self):
        """Overwrites the verify() of BaseAlert to check the post exists

        """
        return m.db.users.find_one({'_id': self.user_id}, {}) and \
            m.db.posts.find_one({'_id': self.post_id}, {})


class TaggingAlert(PostingAlert):
    """Form of all tagging alert messages

    """

    def prettify(self, for_uid=None):
        return '<a href="{0}">{1}</a> tagged you in a <a href="{2}">post</a>' \
               .format(url_for('users.profile',
                               username=self.user.get('username')),
                       do_capitalize(self.user.get('username')), self.url())


class CommentingAlert(PostingAlert):
    """Form of all commenting alert messages

    """

    def prettify(self, for_uid=None):
        # Let's try and work out why this user is being notified of a comment
        reason = subscription_reason(for_uid, self.post_id)

        if reason == SubscriptionReasons.POSTER:
            sr = 'posted'
        elif reason == SubscriptionReasons.COMMENTER:
            sr = 'commented on'
        elif reason == SubscriptionReasons.TAGEE:
            sr = 'were tagged in'
        else:
            # This should never really happen but let's play ball eh?
            sr = 'are subscribed to'

        return '<a href="{0}">{1}</a> ' \
               'commented on a <a href="{2}">post</a> you {3}' \
               .format(url_for('users.profile',
                               username=self.user.get('username')),
                       do_capitalize(self.user.get('username')), self.url(),
                       sr)


def create_post(user_id, username, body, reply_to=None, upload=None):
    """Creates a new post

    This handled both posts and what used to be called comments. If the
    reply_to field is not None then the post will be treat as a comment.
    You will need to make sure the reply_to post exists.

    :param user_id: The user id of the user posting the post
    :type user_id: str
    :param username: The user name of the user posting (saves a lookup)
    :type username: str
    :param body: The content of the post
    :type body: str
    :param reply_to: The post id of the post this is a reply to if any
    :type reply_to: str
    :param upload:
    :returns: The post id of the new post
    :rtype: str or None

    """
    # Get a new UUID for the post_id ("_id" in MongoDB)
    post_id = get_uuid()
    # Get the timestamp, we will use this to populate users feeds
    post_time = timestamp()

    post = {
        '_id': post_id,             # Newly created post id
        'user_id': user_id,         # User id of the poster
        'username': username,       # Username of the poster
        'body': body,               # Body of the post
        'created': post_time,       # Unix timestamp for this moment in time
        'score': 0,                 # Atomic score counter
    }

    if reply_to is not None:
        # If the is a reply it must have this property
        post['reply_to'] = reply_to
    else:
        # Replies don't need a comment count on posts
        post['comment_count'] = 0

    # TODO: Make the upload process better at dealing with issues
    if upload:
        # If there is an upload along with this post it needs to go for
        # processing.
        # process_upload() can throw an Exception of UploadError.
        # TODO: Turn this in to a Celery task
        filename = process_upload(post_id, upload)

        if filename is not None:
            # If the upload process was okay attach the filename to the doc
            post['upload'] = filename
        else:
            # Stop the image upload process here if something went wrong.
            return None

    # Add the post to the database
    # If the post isn't stored, result will be None
    result = m.db.posts.insert(post)

    # Only carry out the rest of the actions if the insert was successful
    if result:
        # Is this a comment?
        if reply_to is None:
            # Handle what Pjuu < v0.6 called a POST

            # Add post to authors feed
            r.zadd(k.USER_FEED.format(user_id), post_time, post_id)
            # Ensure the feed does not grow to large
            r.zremrangebyrank(k.USER_FEED.format(user_id), 0, -1000)

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
            populate_followers_feeds(user_id, post_id, post_time)

        else:
            # Handle what Pjuu < v0.6 called a COMMENT

            # To reduce database look ups on the read path we will increment
            # the reply_to's comment count.
            m.db.posts.update({'_id': reply_to},
                              {'$inc': {'comment_count': 1}})

            # COMMENT ALERTING

            # Alert all subscribers to the post that a new comment has been
            # added. We do this before subscribing anyone new
            alert = CommentingAlert(user_id, reply_to)

            subscribers = []
            # Iterate through subscribers and let them know about the comment
            for subscriber_id in get_subscribers(reply_to):
                # Ensure we don't get alerted for our own comments
                if subscriber_id != user_id:
                    subscribers.append(subscriber_id)

            # Push the comment alert out to all subscribers
            AlertManager().alert(alert, subscribers)

            # Subscribe the user to the post, will not change anything if they
            # are already subscribed
            subscribe(user_id, reply_to, SubscriptionReasons.COMMENTER)

            # TAGGING

            # Create alert
            alert = TaggingAlert(user_id, reply_to)

            # Subscribe tagees
            tagees = parse_tags(body)
            tagees_to_alert = []
            for tagee in tagees:
                # Don't allow tagging yourself
                if tagee[0] != user_id:
                    subscribe(tagee[0], reply_to, SubscriptionReasons.TAGEE)
                    tagees_to_alert.append(tagee[0])

            # Get an alert manager to notify all tagees
            AlertManager().alert(alert, tagees_to_alert)

        # Return the id of the new post
        return post_id

    # If there was a problem putting the post in to Mongo we will return None
    return None  # pragma: no cover


def parse_tags(body, deduplicate=False):
    """Finds '@' tags within a posts body.

    This is used by create_post to alert users that they have been tagged in a
    post and by the 'nameify' template_filter also uses this to identify tags
    before it inserts the links. See nameify_filter() in posts.views

    :type body: str
    :param deduplicate: remove duplicate instances of a tag. Used by the
                        alerting system to only send one alert to a user even
                        if someone repeats the tag. Having this as false allows
                        us to highlight all the tags in the nameify_filter.
    :type deduplicate: bool
    :returns: This returns a list of tuples (uid, username, tag, span)
    :rtype: list

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


def populate_followers_feeds(user_id, post_id, timestamp):
    """Fan out a post_id to all the users followers.

    This can be run on a worker to speed the process up.

    """
    # Get a list of ALL users who are following a user
    followers = r.zrange(k.USER_FOLLOWERS.format(user_id), 0, -1)
    # This is not transactional as to not hold Redis up.
    for follower_id in followers:
        # Add the pid to the list
        r.zadd(k.USER_FEED.format(follower_id), timestamp, post_id)
        # Stop followers feeds from growing to large, doesn't matter if it
        # doesn't exist
        r.zremrangebyrank(k.USER_FEED.format(follower_id), 0, -1000)


def back_feed(who_id, whom_id):
    """Takes 5 lastest posts from user with ``who_id`` places them in user
    with ``whom_id`` feed.

    The reason behind this is that new users may follow someone but still have
    and empty feed, which makes them sad :( so we'll give them some. If the
    posts are to old for a non user they will be removed when the feed is
    trimmed, but they may make it in to the feed but not at the top.

    :param who_id: user who just followed ``who_id``
    :type who_id: str
    :param whom_id: user who was just followed by ``whom_id``
    :type whom_id: str
    :returns: None

    """
    # Get followee's last 5 posts (doesn't matter if there isn't any)
    # We only need the IDs and the created time
    posts = m.db.posts.find({'user_id': whom_id, 'reply_to': None},
                            {'_id': True, 'created': True}) \
        .sort('created', -1).limit(5)

    # Iterate the cursor and append the posts to the users feed
    for post in posts:
        timestamp = post.get('created')
        post_id = post.get('_id')
        # Place on the feed
        r.zadd(k.USER_FEED.format(who_id), timestamp, post_id)
        # Trim the feed to the 1000 max
        r.zremrangebyrank(k.USER_FEED.format(who_id), 0, -1000)


def check_post(user_id, post_id, reply_id=None):
    """Ensure reply_id is a reply_to post_id and that post_id was created by
    user_id.

    .. note:: Think before testing. user_id is the person wrote post_id,
              reply_id if assigned has to have been a reply to post_id.
              This for checking the urls not for checking who wrote reply_id

    """
    # Check if cid is a comment of post pid
    if reply_id:
        # Get the reply_to field of the reply object and check it matches
        reply = m.db.posts.find_one({'_id': reply_id}, {'reply_to': True})
        if reply:
            if reply.get('reply_to') != post_id:
                return False
        else:
            return False

    # Get the user_id for post with post_id to verify
    post = m.db.posts.find_one({'_id': post_id}, {'user_id': True})
    if post is not None and post.get('user_id') == user_id:
        return True

    return False


def get_post(post_id):
    """Returns a post. Simple helper function

    """
    post = m.db.posts.find_one({'_id': post_id})
    # Attach in the e-mail (will be removed with image uploads)

    if post is not None:
        user = m.db.users.find_one({'_id': post.get('user_id')},
                                   {'email': True})
        if user is not None:
            post['user_email'] = user.get('email')

    return post


def get_posts(user_id, page=1):
    """Returns a users posts as a pagination object.

    """
    per_page = app.config.get('PROFILE_ITEMS_PER_PAGE')

    # Get the user object we need the email for Gravatar.
    user = m.db.users.find_one({'_id': user_id},
                               {'email': True})

    total = m.db.posts.find({'user_id': user_id,
                             'reply_to': {'$exists': False}}).count()
    cursor = m.db.posts.find({'user_id': user_id,
                              'reply_to': {'$exists': False}}) \
        .sort('created', -1).skip((page - 1) * per_page).limit(per_page)

    posts = []
    for post in cursor:
        # Get the users email address for the avatar. This will be removed
        # when image uploads are added
        if user is not None:
            post['user_email'] = user.get('email')

        posts.append(post)

    return Pagination(posts, total, page, per_page)


def get_replies(post_id, page=1):
    """Returns all a posts replies as a pagination object.

    """
    per_page = app.config.get('PROFILE_ITEMS_PER_PAGE')
    total = m.db.posts.find_one({'_id': post_id}).get('comment_count')
    cursor = m.db.posts.find(
        {'reply_to': post_id}
    ).sort([('created', -1)]).skip((page - 1) * per_page).limit(per_page)

    replies = []
    for reply in cursor:
        # We have to get the users email for each post for the gravatar
        user = m.db.users.find_one(
            {'_id': reply.get('user_id')},
            {'email': True})

        if user is not None:
            reply['user_email'] = user.get('email')

        replies.append(reply)

    return Pagination(replies, total, page, per_page)


def has_voted(user_id, post_id):
    """Check if a user has voted on a post or a comment, if so return the vote.

    """
    return r.zscore(k.POST_VOTES.format(post_id), user_id)


def vote_post(user_id, post_id, amount=1):
    """Handles voting on posts

    """
    # Get the comment so we can check who the author is
    author_uid = get_post(post_id).get('user_id')

    if not has_voted(user_id, post_id):
        if author_uid != user_id:
            r.zadd(k.POST_VOTES.format(post_id), amount, user_id)
            # Increment the score by amount (can be negative)
            # Post score can go lower than 0
            m.db.posts.update({'_id': post_id},
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

    # In some situations a post may be in a cursor (deleting account) but have
    # already been deleted by this function in a previous run.
    if post is not None:
        # Delete votes and subscribers from Redis
        r.delete(k.POST_VOTES.format(post.get('_id')))

        # Delete the post from MongoDB
        m.db.posts.remove({'_id': post_id})

        if 'upload' in post:
            # If there is an upload, delete it!
            delete_upload(post['upload'])

        if 'reply_to' in post:
            m.db.posts.update({'_id': post['reply_to']},
                              {'$inc': {'comment_count': -1}})
        else:
            # Trigger deletion all posts comments if this post isn't a reply
            r.delete(k.POST_SUBSCRIBERS.format(post.get('_id')))
            delete_post_replies(post_id)


def delete_post_replies(post_id):
    """Delete ALL comments on post with pid.

    This can't be done in one single call to Mongo because we need to remove
    the votes from Redis!

    """
    # Get a cursor for all the posts comments
    cur = m.db.posts.find({'reply_to': post_id})

    # Iterate over the cursor and delete each one
    for reply in cur:
        reply_id = reply.get('_id')

        # Delete the comment itself from MongoDB
        m.db.posts.remove({'_id': reply_id})

        # Remove any uploaded files
        if 'upload' in reply:
            delete_upload(reply['upload'])

        # Delete votes from Redis
        r.delete(k.POST_VOTES.format(reply_id))


def subscribe(user_id, post_id, reason):
    """Subscribes a user (uid) to post (pid) for reason.

    """
    # Check that pid exsits if not do nothing
    if not m.db.posts.find_one({'_id': post_id}, {}):
        return False

    # Only subscribe the user if the user is not already subscribed
    # this will mean the original reason is kept
    return zadd_member_nx(keys=[k.POST_SUBSCRIBERS.format(post_id)],
                          args=[reason, user_id])


def unsubscribe(user_id, post_id):
    """Unsubscribe a user from a post.

    """
    # Actually remove the uid from the subscribers list
    return bool(r.zrem(k.POST_SUBSCRIBERS.format(post_id), user_id))


def get_subscribers(post_id):
    """Return a list of subscribers 'user_id's for a given post

    """
    return r.zrange(k.POST_SUBSCRIBERS.format(post_id), 0, -1)


def is_subscribed(user_id, post_id):
    """Returns a boolean to denote if a user is subscribed or not

    """
    return r.zrank(k.POST_SUBSCRIBERS.format(post_id), user_id) is not None


def subscription_reason(user_id, post_id):
    """Returns the reason a user is subscribed to a post.

    """
    return r.zscore(k.POST_SUBSCRIBERS.format(post_id), user_id)
