# -*- coding: utf8 -*-

"""Key constants which Pjuu uses for Redis as well as some helpful stuff which
makes using Redis a little easier.

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2020 Joe Doherty

"""

# Although not strictly Redis, these expiration constants are useful
# Standard 7 days
# Calculate it, makes it nicer to change
EXPIRE_SECONDS = 7 * 24 * 60 * 60
EXPIRE_MILLISECONDS = EXPIRE_SECONDS * 1000
# Other time periods
EXPIRE_24HRS = 24 * 60 * 60
EXPIRE_4WKS = 28 * 24 * 60 * 60

# Vote expiration timeout
# You can remove your vote within this time (5mins)
VOTE_TIMEOUT = 300

# Standard contants
# We occasionally need to set a key to something which is invalid and which
# we can test for. For example when a user is deleted there username is
# resserved for 7 days
# We will use the lua repr for None
NIL_VALUE = str(None)

# Pjuu permissions on posts.
# Defines who can see a post
PERM_PUBLIC = 0
PERM_PJUU = 1
PERM_APPROVED = 2

# This is to define the patterns for all the keys used inside Redis
# This is best method I can think of to stop the DUPLICATION of strings
# around the code base

# Usage example:
#
#   USER_FEED.format('aaebdfeb479c11e4ad966003089579ee')
#
# Will return the user identified by hex uuid repr

# User related keys

# Returns: list
USER_FEED = "{{user:{0}}}:feed"

# Returns: zset
USER_FOLLOWERS = "{{user:{0}}}:followers"

# Returns: zset
USER_FOLLOWING = "{{user:{0}}}:following"

# Returns: zset
USER_APPROVED = "{{user:{0}}}:approved"

# Returns: zset
USER_ALERTS = "{{user:{0}}}:alerts"

# Post related keys

# Returns: zset
POST_VOTES = "{{post:{0}}}:votes"

# Returns: zset
POST_SUBSCRIBERS = "{{post:{0}}}:subscribers"

# Returns: zset
POST_FLAGS = "{{post:{0}}}:flags"

# Alert related keys

# Return: hash
ALERT = "{{alert:{0}}}"

# Other keys

# Authentication tokens
# Return: str
TOKEN = "{{token:{0}}}"

# Tip names
# Uses around the site to discover valid tip name
# NOT TECHNICALLY A KEY BUT WE NEED TO KNOW
VALID_TIP_NAMES = [
    'welcome'
]
