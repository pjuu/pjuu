# Stdlib imports
from hashlib import md5

# Pjuu imports
from pjuu import app, db
from pjuu.auth import current_user


@app.template_filter('following')
def following_filter(user):
    '''
    Checks if current user is following the user with id piped to filter 
    '''
    return user in current_user.following.all()


@app.template_filter('gravatar')
def gravatar(email, size=24):
    return 'https://www.gravatar.com/avatar/%s?d=identicon&s=%d' % \
        (md5(email.strip().lower().encode('utf-8')).hexdigest(), size)


def follow_user(who, whom):
    """
    Set `who` as a follower of `whom`
    """
    if who is whom:
        return False
    try:
        if whom in who.following.all():
            return False
        who.following.append(whom)
        db.session.add(who)
        db.session.commit()
        return True
    except:
        # Something went wrong
        db.session.rollback()
        abort(500)
        return False


def unfollow_user(who, whom):
    """
    Remove `whom` from `who`'s following list
    """
    if who is whom:
        return False
    try:
        if whom not in who.following.all():
            return False
        who.following.remove(whom)
        db.session.add(who)
        db.session.commit()
        return True
    except:
        # Something went wrong
        db.session.rollback()
        abort(500)
        return False
