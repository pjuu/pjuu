# Stdlib imports
from hashlib import md5
import math

# Pjuu imports
from pjuu import app, r
from pjuu.auth import current_user


@app.template_filter('following')
def following_filter(user_id):
    """
    Checks if current user is following the user with id piped to filter 
    """
    return user in current_user.following.all()


@app.template_filter('gravatar')
def gravatar(email, size=24):
    """
    Returns gravatar URL for a given email with the size size.
    """
    return 'https://www.gravatar.com/avatar/%s?d=identicon&s=%d' % \
        (md5(email.strip().lower().encode('utf-8')).hexdigest(), size)


@app.template_filter('millify')
def millify(n):
    """
    Template filter to millify numbers, e.g. 1K, 2M, 1.25B
    """
    n = int(n)
    if n == 0:
        return n
    number = n
    if n < 0:
        number = abs(n)
    millnames = ['','K','M','B','T','Q','Qt']
    millidx = max(0, min(len(millnames) - 1,
                      int(math.floor(math.log10(abs(number)) / 3.0))))
    result = '%.0f%s' % (number / 10 ** (3 * millidx), millnames[millidx])
    if n < 0:
        return '-' + result
    return result


def get_profile(uid):
    """
    Returns a users profile.
    """
    profile = {
        'user': r.hgetall('user:%d' % uid),
        'post_count': r.llen('posts:%d' % uid),
        'followers_count': r.llen('followers:%d' % uid),
        'following_count': r.llen('following:%d' % uid)
    }
    return profile


def follow_user(who_uid, whom_uid):
    """
    Add whom to who's following set and who to whom's followers set
    """
    pipe = r.pipeline()
    if pipe.zrank('following:%d' % who_uid, whom_uid):
        return False
    pipe.zadd('following:%d' % who_uid, whom_uid,
              pipe.zcard('following:%d' % who_uid))
    pipe.zadd('followers:%d' % whom_uid, who_uid,
              pipe.zcard('following:%d' % who_uid))
    pipe.execute()
    return True


def unfollow_user(who_uid, whom_uid):
    """
    Remove whom from whos following set and remove who from whoms followers set
    """
    if not r.sismember('following:%d' % who_uid, whom_uid):
        return False
    r.srem('following:%d' % who_uid, whom_uid)
    r.srem('followers:%d' % whom_uid, who_uid)
    return True


def get_feed(uid, page=1):
    """
    Returns all posts in a users feed based on page.
    This will be a list of dicts
    """
    pass


def get_posts(uid):
    pass
