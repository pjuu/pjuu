# -*- coding: utf8 -*-

# This file is not used at the moment inside the code.
# This is to define the patterns for all the keys used inside Redis
# This is best method I can think of to stop the DUPLICATION of strings
# around the code base

# Key to get all user information
# Usage: <VARIABLE> % uid(int)

# Returns: sortedset
USER = "user:%d"

# Returns: list
USER_FEED = "user:%d:feed"

# Returns: list
USER_POSTS = "user:%d:posts"

# Returns: list
USER_COMMENTS = "user:%d:comments"

# Returns: sortedset
USER_FOLLOWERS = "user:%d:followers"

# Returns: sortedset
USER_FOLLOWING = "user:%d:following"

# Look-up keys
# Usage: <VARIABLE> % string

# Returns: int
UID_EMAIL = "uid:email:%s"

# Returns: int
UID_USERNAME = "uid:email:%s"

# Post related keys
# Usage: <VARIABLE> % pid(int)

# Returns: hash
POST = "post:%d"

# Returns: sortedset
POST_VOTES = "post:%d:votes"

# Returns: list
POST_COMMENTS = "post:%d:comments"

# Comment related keys
# Usage: <VARIABLE> % cid(int)

# Returns: hash
COMMENT = "comment:%d"

# Returns: sortedset
COMMENT_VOTES = "comment:%d:votes"