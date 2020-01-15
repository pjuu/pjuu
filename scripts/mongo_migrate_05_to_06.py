# -*- coding: utf8 -*-

"""Converts Redis users, posts and comments to MongoDB documents.

This is only needed if moving from Pjuu <0.6 to >=0.6.

.. note: Before running this script ensure you have an up to date Redis backup
         this may corrupt your data.

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2020 Joe Doherty

"""

# Stdlib imports
import ast
import json
import re
from uuid import uuid1
# 3rd party imports
from redis import StrictRedis
from redis.exceptions import ResponseError
import pymongo


r = StrictRedis()
m = pymongo.MongoClient(host='localhost')


USER = "{{user:{0}}}"
USER_FEED = "{{user:{0}}}:feed"
USER_FEED_TEMP = "{{user:{0}}}:feed_temp"
USER_POSTS = "{{user:{0}}}:posts"
USER_COMMENTS = "{{user:{0}}}:comments"
USER_FOLLOWERS = "{{user:{0}}}:followers"
USER_FOLLOWING = "{{user:{0}}}:following"
USER_ALERTS = "{{user:{0}}}:alerts"

UID_EMAIL = "uid:email:{0}"
UID_USERNAME = "uid:username:{0}"

POST = "{{post:{0}}}"
POST_VOTES = "{{post:{0}}}:votes"
POST_COMMENTS = "{{post:{0}}}:comments"
POST_SUBSCRIBERS = "{{post:{0}}}:subscribers"

COMMENT = "{{comment:{0}}}"
COMMENT_VOTES = "{{comment:{0}}}:votes"

ALERT = "{{alert:{0}}}"

TOKEN = "{{token:{0}}}"


USER_RE = re.compile(r"\{user\:([0-9a-f]*)\}$")
POST_RE = re.compile(r"\{post\:([0-9a-f]*)\}$")
COMMENT_RE = re.compile(r"\{comment\:([0-9a-f]*)\}$")


def flag_to_bool(flag):
    """Converts the user flags to Boolean values.

    These come in the following forms:
        "0" = False
        "1" = True
        None = False

    0, 1 are strings so need to be converted before the bool

    """
    if flag is not None:
        return bool(int(flag))
    return False


if __name__ == '__main__':

    # Iterate ALL posts first and convert them to there new BSON repr.
    # DUPLICATES SHOULD NEVER HAPPEN HERE.
    for key in r.keys('{post:*}'):
        if POST_RE.match(key) is not None:
            print('Converting post:', key)
            # Get the original post from Redis
            post = r.hgetall(key)
            # Convert `uid` to new `user_id`
            post['user_id'] = post.get('uid')
            del post['uid']

            # Look up the `username` for the `user_id` and attach this to the
            # post. We now store this de-normalized to reduce reads
            post['username'] = \
                r.hget(USER.format(post.get('user_id')), 'username')

            # `pid` becomes `_id`
            post_id = post.get('pid')
            post['_id'] = post_id
            del post['pid']

            # Get the count of comments for the post and add the new key
            # This is now de-normalized
            post['comment_count'] = \
                r.llen(POST_COMMENTS.format(post_id))

            post['created'] = float(post.get('created'))
            post['score'] = int(post.get('score'))

            if m.pjuu.posts.insert(post):
                r.delete(POST.format(post_id))
                r.delete(POST_COMMENTS.format(post_id))

    # Convert all comments to become posts.
    # DUPLICATES CAN HAPPEN HERE AND ARE EXPECTED. COMMENTS WHICH COLLIDE WILL
    # BE GIVEN A NEW `_id`.
    # There is a duplication of code here but as its a script I want
    # readability to be a priority (this could brick some installations).
    for key in r.keys('{comment:*}'):
        if COMMENT_RE.match(key) is not None:
            print('Converting comment:', key)
            # Get the original comment from Redis (called post here)
            post = r.hgetall(key)
            # Convert `uid` to new `user_id`
            post['user_id'] = post.get('uid')
            del post['uid']

            # Look up the `username` for the `user_id` and attach this to the
            # post. We now store this de-normalized to reduce reads
            post['username'] = \
                r.hget(USER.format(post.get('user_id')), 'username')

            # `cid` becomes `_id`
            # Duplicates possible. We will only give a new ID at insert time.
            post_id = post.get('cid')
            post['_id'] = post_id
            del post['cid']

            # The column which was called `pid` is now called `reply_to`
            post['reply_to'] = post.get('pid')
            del post['pid']

            post['created'] = float(post.get('created'))
            post['score'] = int(post.get('score'))

            try:
                if m.pjuu.posts.insert(post):
                    r.delete(COMMENT.format(post_id))
            except (pymongo.errors.DuplicateKeyError):
                # At the time this script was written uuid1().hex is how the
                # `pjuu.lib.get_uuid()` works.
                post['_id'] = uuid1().hex
                # We won't try again. If this fails its bricked.
                if m.pjuu.posts.insert(post):
                    r.delete(COMMENT.format(post_id))

            # Comments are now posts so we need to change the names of the
            # voting keys. We will also change it to match the _id in the case
            # that it was changed above
            if r.exists(COMMENT_VOTES.format(post_id)):
                r.rename(COMMENT_VOTES.format(post_id),
                         POST_VOTES.format(post['_id']))

    # Iterate ALL user keys, we can't do this above because we need all posts
    # migrated before the user migration will work
    for key in r.keys('{user:*}'):
        user_match = USER_RE.match(key)
        if user_match is not None:
            print('Converting user:', key)
            user_id = user_match.groups(1)[0]
            user = r.hgetall(USER.format(user_id))

            # Convert the older user hash to a Mongo document
            user['_id'] = user.get('uid')
            del user['uid']  # Remove the old 'uid' field

            # Set score
            user['score'] = int(user.get('score'))

            # Timestamps
            user['created'] = float(user.get('created'))
            user['alerts_last_checked'] = \
                float(user.get('alerts_last_checked', -1))
            user['last_login'] = float(user.get('last_login'))

            # Flags. These need to be converted to int first
            user['active'] = flag_to_bool(user.get('active'))
            user['banned'] = flag_to_bool(user.get('banned'))
            user['muted'] = flag_to_bool(user.get('muted'))
            user['op'] = flag_to_bool(user.get('op'))

            # Store the new user document in MongoDB
            if m.pjuu.users.insert(user):
                # Reformat the users feed
                for post_id in r.lrange(USER_FEED.format(user_id), 0, -1):
                    post = m.pjuu.posts.find_one({'_id': post_id})
                    # Ignore posts that DO NOT exist.
                    # The user will not have logged in since the post has been
                    # deleted (self cleaning never happened)
                    if post:
                        r.zadd(USER_FEED_TEMP.format(user_id),
                               post.get('created'), post.get('_id'))
                # Rename temp feed to feed
                try:
                    r.rename(USER_FEED_TEMP.format(user_id),
                             USER_FEED.format(user_id))
                except ResponseError:
                    pass

                # Delete keys which are no longer needed
                r.delete(USER.format(user_id))
                r.delete(USER_COMMENTS.format(user_id))
                r.delete(USER_POSTS.format(user_id))
                r.delete(UID_USERNAME.format(user.get('username')))
                r.delete(UID_EMAIL.format(user.get('email')))

    # Clean-up some old keys which are no longer needed
    # These were used in an earlier version of Pjuu.
    # You may not have these within Redis, it doesn't matter though.
    r.delete('global:uid')
    r.delete('global:pid')
    r.delete('global:cid')

    # Convert the alert pickles to the new naming convention
    for key in r.keys("{alert:*"):
        print('Converting alert:', key)
        # Get the alert from Redis and convert it to a dict
        alert_pickle = r.get(key)
        alert = ast.literal_eval(alert_pickle)

        # Convert ``uid`` to ``user_id``
        alert['user_id'] = alert['uid']
        del alert['uid']

        # Convert ``aid`` to ``alert_id``
        alert['alert_id'] = alert['aid']
        del alert['aid']

        # Convert ``pid`` to ``post_id``
        if 'pid' in alert:
            alert['post_id'] = alert['pid']
            del alert['pid']

        # Make the string a valid Pickle
        alert = json.dumps(alert)

        # Update the alert in Redis
        r.delete(key)
        r.set(key, alert)
