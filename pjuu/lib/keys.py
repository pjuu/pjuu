# -*- coding: utf8 -*-

"""
Description:
    Key constants which Pjuu uses for Redis as well as some helpful stuff
    which makes using Redis a little easier.

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

# Although not strictly Redis, these expiration constants are useful
# Standard 7 days
# Calculate it, makes it nicer to change
EXPIRE_SECONDS = 7 * 24 * 60 * 60
EXPIRE_MILLISECONDS = EXPIRE_SECONDS * 1000
# Other time periods
EXPIRE_24HRS = 24 * 60 * 60
EXPIRE_4WKS = 28 * 24 * 60 * 60

# Standard contants
# We occasionally need to set a key to something which is invalid and which
# we can test for. For example when a user is deleted there username is
# resserved for 7 days
# We will use the lua repr for None
NIL_VALUE = str(None)

# This is to define the patterns for all the keys used inside Redis
# This is best method I can think of to stop the DUPLICATION of strings
# around the code base

# Usage example:
#
#   USER.format('aaebdfeb479c11e4ad966003089579ee')
#
# Will return the user identified by hex uuid repr

# Keys to get all user information

# Returns: hash
USER = "{{user:{0}}}"

# Returns: list
USER_FEED = "{{user:{0}}}:feed"

# Returns: list
USER_POSTS = "{{user:{0}}}:posts"

# Returns: list
USER_COMMENTS = "{{user:{0}}}:comments"

# Returns: zset
USER_FOLLOWERS = "{{user:{0}}}:followers"

# Returns: zset
USER_FOLLOWING = "{{user:{0}}}:following"

# Returns: zset
USER_ALERTS = "{{user:{0}}}:alerts"

# Look-up keys

# Returns: uid(str)
UID_EMAIL = "uid:email:{0}"

# Returns: uid(str)
UID_USERNAME = "uid:username:{0}"

# Post related keys

# Returns: hash
POST = "{{post:{0}}}"

# Returns: zset
POST_VOTES = "{{post:{0}}}:votes"

# Returns: list
POST_COMMENTS = "{{post:{0}}}:comments"

# Returns: zset
POST_SUBSCRIBERS = "{{post:{0}}}:subscribers"

# Comment related keys

# Returns: hash
COMMENT = "{{comment:{0}}}"

# Returns: zset
COMMENT_VOTES = "{{comment:{0}}}:votes"

# Alert related keys

# Return: hash
ALERT = "{{alert:{0}}}"


# Other keys

# Authentication tokens
# Return: str
TOKEN = "{{token:{0}}}"
