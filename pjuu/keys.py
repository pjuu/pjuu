# -*- coding: utf8 -*-

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

# Although not strictly Redis, these expiration constants are useful
EXPIRE_SECONDS = 604800
EXPIRE_MILLISECONDS = 604800000

# This is to define the patterns for all the keys used inside Redis
# This is best method I can think of to stop the DUPLICATION of strings
# around the code base

# Counter keys for IDs
GLOBAL_UID = "global:uid"
GLOBAL_PID = "global:pid"
GLOBAL_CID = "global:cid"

# Keys to get all user information
# Usage: <VARIABLE> % int

# Returns: hash
USER = "user:%d"

# Returns: list
USER_FEED = "user:%d:feed"

# Returns: list
USER_POSTS = "user:%d:posts"

# Returns: list
USER_COMMENTS = "user:%d:comments"

# Returns: zset
USER_FOLLOWERS = "user:%d:followers"

# Returns: zset
USER_FOLLOWING = "user:%d:following"

# Look-up keys
# Usage: <VARIABLE> % string

# Returns: int
UID_EMAIL = "uid:email:%s"

# Returns: int
UID_USERNAME = "uid:username:%s"

# Post related keys
# Usage: <VARIABLE> % pid(int)

# Returns: hash
POST = "post:%d"

# Returns: zset
POST_VOTES = "post:%d:votes"

# Returns: list
POST_COMMENTS = "post:%d:comments"

# Comment related keys
# Usage: <VARIABLE> % cid(int)

# Returns: hash
COMMENT = "comment:%d"

# Returns: zset
COMMENT_VOTES = "comment:%d:votes"
