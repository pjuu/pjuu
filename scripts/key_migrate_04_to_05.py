# -*- coding: utf8 -*-

"""Migrate the Redis key names from version before and including 0.4 to the new
naming conversion used by 0.5.

The only changes are that keys related are key spaced using Redis hashtags.
For example;

    user:1 would become {user:1}
    user:1:followers would become {user:1}:followers
    post:1 would become {post:1}
    post:1:comments would become {post:1}:comments

So on and so forth. See pjuu/lib/lua.py for more details.

Alerts would need to be further converted so I am simply going to remove
all alerts! These are not super important and it is not going to affect
many people at this time. They expire after 4 weeks anyway.

NOTE: THIS SCRIPT IS HORRIBLY INEFFICIENT BUT WITH THE DATA SET AS IT IS AT
      THE MOMMENT.

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2020 Joe Doherty

"""

# Stdlib imports
import re
# 3rd party imports
import redis


###############################################################################
# Key constants (from lib/keys)
###############################################################################

USER = "{{user:{0}}}"
USER_FEED = "{{user:{0}}}:feed"
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

###############################################################################
# Regular expressions for identifying keys
###############################################################################

USER_RE = re.compile(r"user\:([0-9a-f]*)$")
POST_RE = re.compile(r"post\:([0-9a-f]*)$")
COMMENT_RE = re.compile(r"comment\:([0-9a-f]*)$")
ALERT_RE = re.compile(r"alert\:([0-9a-f]*)$")


if __name__ == "__main__":

    # Change this to match the Redis settings you use
    r = redis.StrictRedis()

    print("Pjuu, Redis key migration script v0.4 to v0.5")
    print("---")
    print("Getting all keys...")
    keys = r.keys("*")

    print("Converting keys...")
    for key in keys:
        #######################################################################
        # Users
        #######################################################################
        user = USER_RE.match(key)
        if user:
            print("Migrating user key")
            if r.exists(key):
                r.rename(key,
                         USER.format(user.groups(1)[0]))
            if r.exists(key + ":feed"):
                r.rename(key + ":feed",
                         USER_FEED.format(user.groups(1)[0]))
            if r.exists(key + ":posts"):
                r.rename(key + ":posts",
                         USER_POSTS.format(user.groups(1)[0]))
            if r.exists(key + ":comments"):
                r.rename(key + ":comments",
                         USER_COMMENTS.format(user.groups(1)[0]))
            if r.exists(key + ":followers"):
                r.rename(key + ":followers",
                         USER_FOLLOWERS.format(user.groups(1)[0]))
            if r.exists(key + ":following"):
                r.rename(key + ":following",
                         USER_FOLLOWING.format(user.groups(1)[0]))
            if r.exists(key + ":alerts"):
                r.rename(key + ":alerts",
                         USER_ALERTS.format(user.groups(1)[0]))
            continue
        #######################################################################
        # Posts
        #######################################################################
        post = POST_RE.match(key)
        if post:
            print("Migrating post key")
            if r.exists(key):
                r.rename(key,
                         POST.format(post.groups(1)[0]))
            if r.exists(key + ":votes"):
                r.rename(key + ":votes",
                         POST_VOTES.format(post.groups(1)[0]))
            if r.exists(key + ":comments"):
                r.rename(key + ":comments",
                         POST_COMMENTS.format(post.groups(1)[0]))
            if r.exists(key + ":subscribers"):
                r.rename(key + ":subscribers",
                         POST_SUBSCRIBERS.format(post.groups(1)[0]))
            continue
        #######################################################################
        # Comments
        #######################################################################
        comment = COMMENT_RE.match(key)
        if comment:
            print("Migrating comment key")
            if r.exists(key):
                r.rename(key,
                         COMMENT.format(comment.groups(1)[0]))
            if r.exists(key + ":votes"):
                r.rename(key + ":votes",
                         COMMENT_VOTES.format(comment.groups(1)[0]))
            continue
        #######################################################################
        # Alerts
        #######################################################################
        alert = ALERT_RE.match(key)
        if alert:
            print("Removing alert key")
            if r.exists(key):
                r.delete(key)
            continue
