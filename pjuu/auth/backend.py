# Stdlib imports
from functools import wraps
from urlparse import urlparse, urljoin

# 3rd party imports
from flask import _app_ctx_stack, request, session
from werkzeug.local import LocalProxy
from werkzeug.security import check_password_hash

# Pjuu imports
from pjuu import app
from pjuu.users.models import User


current_user = LocalProxy(lambda: _get_user())


def _get_user():
    return getattr(_app_ctx_stack.top, 'user', None)


@app.before_request
def _load_useer():
    user = None
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
    _app_ctx_stack.top.user = user


def authenticate(username, password):
    if '@' in username:
        user = User.query.filter(User.email.ilike(username)).first()
    else:
        user = User.query.filter(User.username.ilike(username)).first()
    if user and check_password_hash(user.password, password):
        return user
    return None


def login(user):
    session['user_id'] = user.id


def logout():
    session.pop('user_id', None)


def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
           ref_url.netloc == test_url.netloc
