# Stdlib imports
from urlparse import urlparse, urljoin

# 3rd party imports
from flask import _app_ctx_stack, request, session, abort
from werkzeug.local import LocalProxy
from werkzeug.security import check_password_hash

# Pjuu imports
from pjuu import app, db
from pjuu.users.models import User


# Can be used anywhere to get the current logged in user.
# This will return None if the user is not logged in.
current_user = LocalProxy(lambda: _get_user())


def _get_user():
    """
    Used to create the current_user local proxy.
    """
    return getattr(_app_ctx_stack.top, 'user', None)


@app.before_request
def _load_useer():
    """
    If the user is logged in, will place the user object on the
    application context.
    """
    user = None
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
    _app_ctx_stack.top.user = user


def create_account(username, email, password):
    """
    Creates a user account. If this task fails a 500 will be thrown.
    Returns the user account.
    """
    try:
        new_user = User(username, email, password)
        db.session.add(new_user)
        db.session.commit()
    except Exception as e:
        print e
        db.session.rollback()
        abort(500)
    return new_user


def authenticate(username, password):
    """
    Will authenticate a username/password combination.
    If successful will return a user object else will return None.
    """
    if '@' in username:
        user = User.query.filter(User.email.ilike(username)).first()
    else:
        user = User.query.filter(User.username.ilike(username)).first()
    if user and check_password_hash(user.password, password):
        return user
    return None


def login(user):
    """
    Logs the user in. Will add user id to session.
    Will also update the users last_login time.
    """
    session['user_id'] = user.id
    try:
        user.last_login = db.func.now()
        db.session.add(user)
        db.session.commit()
    except:
        db.session.rollback()
        abort(500)


def logout():
    """
    Removes the user id from the session. If it isn't there then
    nothing bad happens.
    """
    session.pop('user_id', None)


def is_safe_url(target):
    """
    Not sure what the point of checking a URL is at the moment.
    I am using this because at some point it will be important.
    TODO: Test this properly
    """
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
           ref_url.netloc == test_url.netloc
