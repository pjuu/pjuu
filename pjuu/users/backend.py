# Pjuu imports
from pjuu import app, redis as r
from pjuu.auth import current_user
from pjuu.lib.pagination import Pagination


def get_profile(uid):
    """
    Returns a users profile as Dict.
    """
    profile = r.hgetall('user:%d' % uid)
    profile['post_count'] = r.llen('posts:%d' % uid)
    profile['followers_count'] = r.zcard('followers:%d' % uid)
    profile['following_count'] = r.zcard('following:%d' % uid)
    return profile


def get_feed(uid, page=1):
    """
    Returns a users feed as a Pagination.
    """
    return {}


def get_posts(uid, page=1):
    """
    Returns a users posts as a Pagination.
    """
    return {}


def get_following(uid, page=1):
    """
    Returns a list of users uid is following as a Pagination.
    """
    return {}


def get_followers(uid, page=1):
    """
    Returns a list of users whom follow uid as a Pagination.
    """
    return {}


def follow_user(who_uid, whom_uid):
    """
    Add whom to who's following set and who to whom's followers set
    """
    who_uid = int(who_uid)
    whom_uid = int(whom_uid)
    if r.zrank('following:%d' % who_uid, whom_uid):
        return False
    # TODO remove ZCARD call... this is unworkable
    # Integer based time would be brilliant
    r.zadd('following:%d' % who_uid, whom_uid,
           r.zcard('following:%d' % who_uid))
    r.zadd('followers:%d' % whom_uid, who_uid,
           r.zcard('following:%d' % who_uid))
    return True


def unfollow_user(who_uid, whom_uid):
    """
    Remove whom from whos following set and remove who from whoms followers set
    """
    if not r.zrank('following:%d' % who_uid, whom_uid):
        return False
    # Delete uid from who following and whom followers
    r.zrem('following:%d' % who_uid, whom_uid)
    r.zrem('followers:%d' % whom_uid, who_uid)
    return True


def is_following(who_uid, whom_uid):
    """
    Check to see if who is following whom. These need to be uids
    """
    return True if r.zrank("following:%s" % who_id, whom_id) else False