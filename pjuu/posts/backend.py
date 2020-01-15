# -*- coding: utf-8 -*-

"""Simple functions for dealing with posts, replies, votes and subscriptions
within Redis and MongoDB

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2020 Joe Doherty

"""


# 3rd party imports
from flask import current_app as app, url_for
from jinja2.filters import do_capitalize

# Pjuu imports
from pjuu import mongo as m, redis as r, celery
from pjuu.lib import keys as k, timestamp, get_uuid
from pjuu.lib.alerts import BaseAlert, AlertManager
from pjuu.lib.pagination import Pagination
from pjuu.lib.parser import parse_post
from pjuu.lib.uploads import process_upload, delete_upload


# Allow chaning the maximum length of a post
MAX_POST_LENGTH = 500


class CantVoteOnOwn(Exception):
    """Raised when a user tries to vote on a post they authored

    """
    pass


class AlreadyVoted(Exception):
    """Raised when a user tries to vote on a post they have already voted on

    """
    pass


class CantFlagOwn(Exception):
    """Can't flag your own post."""
    pass


class AlreadyFlagged(Exception):
    """You can't flag a post twice."""
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


def create_post(user_id, username, body, reply_to=None, upload=None,
                permission=k.PERM_PUBLIC):
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
    :param permission: Who can see/interact with the post you are posting
    :type permission: int
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
        # Replies don't need a comment count
        post['comment_count'] = 0
        # Set the permission a user needs to view
        post['permission'] = permission

    if upload:
        # If there is an upload along with this post it needs to go for
        # processing.
        # process_upload() can throw an Exception of UploadError. We will let
        # it fall through as a 500 is okay I think.
        # TODO: Turn this in to a Queue task at some point
        filename, animated_filename = process_upload(upload)

        if filename is not None:
            # If the upload process was okay attach the filename to the doc
            post['upload'] = filename
            if animated_filename:
                post['upload_animated'] = animated_filename
        else:
            # Stop the image upload process here if something went wrong.
            return None

    # Process everything thats needed in a post
    links, mentions, hashtags = parse_post(body)

    # Only add the fields if we need too.
    if links:
        post['links'] = links

    if mentions:
        post['mentions'] = mentions

    if hashtags:
        post['hashtags'] = hashtags

    # Add the post to the database
    # If the post isn't stored, result will be None
    result = m.db.posts.insert(post)

    # Only carry out the rest of the actions if the insert was successful
    if result:
        if reply_to is None:
            # Add post to authors feed
            r.zadd(k.USER_FEED.format(user_id), {str(post_id): post_time})
            # Ensure the feed does not grow to large
            r.zremrangebyrank(k.USER_FEED.format(user_id), 0, -1000)

            # Subscribe the poster to there post
            subscribe(user_id, post_id, SubscriptionReasons.POSTER)

            # Alert everyone tagged in the post
            alert_tagees(mentions, user_id, post_id)

            # Append to all followers feeds or approved followers based
            # on the posts permission
            if permission < k.PERM_APPROVED:
                populate_followers_feeds.delay(user_id, post_id, post_time)
            else:
                populate_approved_followers_feeds.delay(
                    user_id, post_id, post_time
                )

        else:
            # To reduce database look ups on the read path we will increment
            # the reply_to's comment count.
            m.db.posts.update({'_id': reply_to},
                              {'$inc': {'comment_count': 1}})

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

            # Alert everyone tagged in the post
            alert_tagees(mentions, user_id, reply_to)

        return post_id

    # If there was a problem putting the post in to Mongo we will return None
    return None  # pragma: no cover


@celery.task()
def populate_followers_feeds(user_id, post_id, timestamp):
    """Fan out a post_id to all the users followers.

    This can be run on a worker to speed the process up.

    """
    # Get a list of ALL users who are following a user
    followers = r.zrange(k.USER_FOLLOWERS.format(user_id), 0, -1)
    # This is not transactional as to not hold Redis up.
    for follower_id in followers:
        # Add the pid to the list
        r.zadd(k.USER_FEED.format(follower_id), {str(post_id): timestamp})
        # Stop followers feeds from growing to large, doesn't matter if it
        # doesn't exist
        r.zremrangebyrank(k.USER_FEED.format(follower_id), 0, -1000)


@celery.task()
def populate_approved_followers_feeds(user_id, post_id, timestamp):
    """Fan out a post_id to all the users approved followers."""
    # Get a list of ALL users who are following a user
    followers = r.zrange(k.USER_APPROVED.format(user_id), 0, -1)
    # This is not transactional as to not hold Redis up.
    for follower_id in followers:
        # Add the pid to the list
        r.zadd(k.USER_FEED.format(follower_id), {str(post_id): timestamp})
        # Stop followers feeds from growing to large, doesn't matter if it
        # doesn't exist
        r.zremrangebyrank(k.USER_FEED.format(follower_id), 0, -1000)


def alert_tagees(tagees, user_id, post_id):
    """Creates a new tagging alert from `user_id` and `post_id` and alerts all
    in the `tagees` list.

    This will take the tagees processed as `mentions`, it will ensure no
    duplication and that the poster is not alerted if they tag themselves.

    :type tagees: list
    :type user_id: str
    :type post_id: str

    """
    alert = TaggingAlert(user_id, post_id)

    seen_user_ids = []
    for tagee in tagees:
        tagged_user_id = tagee.get('user_id')

        # Don't alert users more than once
        if tagged_user_id in seen_user_ids:
            continue

        # Don't alert posting user to tag
        if tagged_user_id == user_id:
            continue

        # Subscribe the tagee to the post won't change anything if they are
        # already subscribed
        subscribe(tagged_user_id, post_id, SubscriptionReasons.TAGEE)

        seen_user_ids.append(tagged_user_id)

    # Get an alert manager to notify all tagees
    AlertManager().alert(alert, seen_user_ids)


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
    # Get followee's last 5 un-approved posts (doesn't matter if isn't any)
    # We only need the IDs and the created time
    posts = m.db.posts.find(
        {'user_id': whom_id, 'reply_to': None,
         'permission': {'$lte': k.PERM_PJUU}},
        {'_id': True, 'created': True},
    ).sort('created', -1).limit(5)

    # Iterate the cursor and append the posts to the users feed
    for post in posts:
        timestamp = post.get('created')
        post_id = post.get('_id')
        # Place on the feed
        r.zadd(k.USER_FEED.format(who_id), {str(post_id): timestamp})
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
                                   {'avatar': True, 'donated': True})
        if user is not None:
            post['user_avatar'] = user.get('avatar')
            post['user_donated'] = user.get('donated', False)

    return post


def get_global_feed(page=1, per_page=None, perm=0):
    if per_page is None:  # pragma: no cover
        per_page = app.config.get('FEED_ITEMS_PER_PAGE')

    lookup_dict = {
        'reply_to': {'$exists': False},
        'permission': {'$lte': perm}
    }

    total = m.db.posts.find(lookup_dict).count()
    cursor = m.db.posts.find(lookup_dict).sort(
        'created', -1).skip((page - 1) * per_page).limit(per_page)

    posts = []
    for post in cursor:
        posts.append(post)

    # Get a list of unique `user_id`s from all the post.
    user_ids = list(set([post.get('user_id') for post in posts]))
    cursor = m.db.users.find({'_id': {'$in': user_ids}},
                             {'avatar': True, 'donated': True})
    # Create a lookup dict `{username: email}`
    users = \
        dict((user.get('_id'), {
            'avatar': user.get('avatar'),
            'donated': user.get('donated', False)
        }) for user in cursor)

    # Add the e-mails to the posts
    processed_posts = []
    for post in posts:
        post['user_avatar'] = users.get(post.get('user_id')).get('avatar')
        post['user_donated'] = users.get(post.get('user_id')).get('donated')
        processed_posts.append(post)

    return Pagination(posts, total, page, per_page)


def get_posts(user_id, page=1, per_page=None, perm=0):
    """Returns a users posts as a pagination object."""
    if per_page is None:
        per_page = app.config.get('FEED_ITEMS_PER_PAGE')

    # Get the user object we need the email for Gravatar.
    user = m.db.users.find_one({'_id': user_id},
                               {'avatar': True, 'donated': True})

    lookup_dict = {
        'user_id': user_id,
        'reply_to': {'$exists': False}
    }

    lookup_dict['permission'] = {'$lte': perm}

    total = m.db.posts.find(lookup_dict).count()
    cursor = m.db.posts.find(lookup_dict).sort(
        'created', -1).skip((page - 1) * per_page).limit(per_page)

    posts = []
    for post in cursor:
        post['user_avatar'] = user.get('avatar')
        post['user_donated'] = user.get('donated', False)
        posts.append(post)

    return Pagination(posts, total, page, per_page)


def get_replies(post_id, page=1, per_page=None, sort_order=-1):
    """Returns all a posts replies as a pagination object."""
    if per_page is None:
        per_page = app.config.get('REPLIES_ITEMS_PER_PAGE')

    total = m.db.posts.find_one({'_id': post_id}).get('comment_count')
    cursor = m.db.posts.find(
        {'reply_to': post_id}
    ).sort(
        [('created', sort_order)]
    ).skip((page - 1) * per_page).limit(per_page)

    replies = []
    for reply in cursor:
        # We have to get the users email for each post for the gravatar
        user = m.db.users.find_one(
            {'_id': reply.get('user_id')},
            {'avatar': True, 'donated': True})

        if user is not None:  # pragma: no branch
            reply['user_avatar'] = user.get('avatar')
            reply['user_donated'] = user.get('donated', False)
            replies.append(reply)

    return Pagination(replies, total, page, per_page)


def get_hashtagged_posts(hashtag, page=1, per_page=None):
    """Returns all posts with `hashtag` in date order."""
    if per_page is None:
        per_page = app.config.get('FEED_ITEMS_PER_PAGE')

    total = m.db.posts.find({
        'hashtags.hashtag': hashtag,
        'reply_to': {'$exists': False}}).count()
    cursor = m.db.posts.find({
        'hashtags.hashtag': hashtag,
        'reply_to': {'$exists': False}
    }).sort('created', -1).skip((page - 1) * per_page).limit(per_page)

    posts = []
    for post in cursor:
        user = m.db.users.find_one(
            {'_id': post.get('user_id')},
            {'avatar': True})

        if post is not None:  # pragma: no branch
            post['user_avatar'] = user.get('avatar')
            posts.append(post)

    return Pagination(posts, total, page, per_page)


def has_voted(user_id, post_id):
    """Check if a user has voted on a post or a comment, if so return the vote.

    """
    return r.zscore(k.POST_VOTES.format(post_id), user_id)


def vote_post(user_id, post_id, amount=1, ts=None):
    """Handles voting on posts

    :param user_id: User who is voting
    :type user_id: str
    :param post_id: ID of the post the user is voting on
    :type post_id: int
    :param amount: The way to vote (-1 or 1)
    :type amount: int
    :param ts: Timestamp to use for vote (ONLY FOR TESTING)
    :type ts: int
    :returns: -1 if downvote, 0 if reverse vote and +1 if upvote

    """
    if ts is None:
        ts = timestamp()

    # Get the comment so we can check who the author is
    author_uid = get_post(post_id).get('user_id')

    # Votes can ONLY ever be -1 or 1 and nothing else
    # we use the sign to store the time and score in one zset score
    amount = 1 if amount >= 0 else -1

    voted = has_voted(user_id, post_id)

    if not voted:
        if author_uid != user_id:
            # Store the timestamp of the vote with the sign of the vote
            r.zadd(k.POST_VOTES.format(post_id), {
                str(user_id): amount * timestamp()
            })

            # Update post score
            m.db.posts.update({'_id': post_id},
                              {'$inc': {'score': amount}})

            # Update user score
            m.db.users.update({'_id': author_uid},
                              {'$inc': {'score': amount}})

            return amount
        else:
            raise CantVoteOnOwn
    elif voted and abs(voted) + k.VOTE_TIMEOUT > ts:
        # No need to check if user is current user because it can't
        # happen in the first place
        # Remove the vote from Redis
        r.zrem(k.POST_VOTES.format(post_id), user_id)

        previous_vote = -1 if voted < 0 else 1

        # Calculate how much to increment/decrement the scores by
        # Saves multiple trips to Mongo
        if amount == previous_vote:
            if previous_vote < 0:
                amount = 1
                result = 0
            else:
                amount = -1
                result = 0
        else:
            # We will only register the new vote if it is NOT a vote reversal.
            r.zadd(k.POST_VOTES.format(post_id), {
                str(user_id): amount * timestamp()
            })

            if previous_vote < 0:
                amount = 2
                result = 1
            else:
                amount = -2
                result = -1

        # Update post score
        m.db.posts.update({'_id': post_id},
                          {'$inc': {'score': amount}})

        # Update user score
        m.db.users.update({'_id': author_uid},
                          {'$inc': {'score': amount}})

        return result
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
    return r.zadd(k.POST_SUBSCRIBERS.format(post_id), {
        str(user_id): reason
    }, nx=True)


def unsubscribe(user_id, post_id):
    """Unsubscribe a user from a post.

    """
    # Actually remove the uid from the subscribers list
    return bool(r.zrem(k.POST_SUBSCRIBERS.format(post_id), user_id))


def flag_post(user_id, post_id):
    """Flags a post for moderator review.

    :returns: True if flagged, false if removed.
              `CantFlagOwn` in case of error.
    """
    # Get the comment so we can check who the author is
    post = get_post(post_id)

    if post.get('user_id') != user_id:
        if not has_flagged(user_id, post_id):
            # Increment the flag count by one and store the user name
            r.zadd(k.POST_FLAGS.format(post_id), {
                str(user_id): timestamp()
            })
            m.db.posts.update({'_id': post_id},
                              {'$inc': {'flags': 1}})
        else:
            raise AlreadyFlagged
    else:
        raise CantFlagOwn


def unflag_post(post_id):
    """Resets the flag count on a post to 0.

    .. note: This is an OP user only action from the dashboard.
    """
    return m.db.posts.update({'_id': post_id}, {'$set': {'flags': 0}})


def get_subscribers(post_id):
    """Return a list of subscribers 'user_id's for a given post

    """
    return r.zrange(k.POST_SUBSCRIBERS.format(post_id), 0, -1)


def is_subscribed(user_id, post_id):
    """Returns a boolean to denote if a user is subscribed or not

    """
    return r.zrank(k.POST_SUBSCRIBERS.format(post_id), user_id) is not None


def has_flagged(user_id, post_id):
    """"""
    return r.zrank(k.POST_FLAGS.format(post_id), user_id) is not None


def subscription_reason(user_id, post_id):
    """Returns the reason a user is subscribed to a post.

    """
    return r.zscore(k.POST_SUBSCRIBERS.format(post_id), user_id)
