# Stdlib imports
from hashlib import md5

# Pjuu imports
from pjuu import app
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
