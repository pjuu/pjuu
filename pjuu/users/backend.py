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
    millnames=['','K','M','B','T','Qa','Qi']
    millidx=max(0,min(len(millnames)-1,
                      int(math.floor(math.log10(abs(number))/3.0))))
    result = '%.0f%s'%(number/10**(3*millidx), millnames[millidx])
    if n < 0:
        return '-' + result
    return result


def follow_user(who_id, whom_id):
    """
    Add whom to who's following set and who to whom's followers set
    """
    pass

def unfollow_user(who_id, whom_id):
    """
    Remove whom from who's following set and remove who from whos followers set
    """
    pass
