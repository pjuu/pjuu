# -*- coding: utf8 -*-
# Stdlib imports
from base64 import (urlsafe_b64encode as b64encode,
                    urlsafe_b64decode as b64decode)
from urlparse import urlparse, urljoin
from time import gmtime
from calendar import timegm
import re
# 3rd party imports
from flask import _app_ctx_stack, request, session, abort
from itsdangerous import TimedSerializer
from werkzeug.local import LocalProxy
from werkzeug.security import generate_password_hash, check_password_hash
# Pjuu imports
from pjuu import app, redis as r


# E-mail checker
email_re = re.compile(r'^.+@[^.].*\.[a-z]{2,10}$')


# Reserved names
# TODO Come up with a better solution for this
reserved_names = []


# Signers
activate_signer = TimedSerializer(app.config['TOKEN_KEY'], salt=app.config['SALT_ACTIVATE'])
forgot_signer = TimedSerializer(app.config['TOKEN_KEY'], salt=app.config['SALT_FORGOT'])
email_signer = TimedSerializer(app.config['TOKEN_KEY'], salt=app.config['SALT_EMAIL'])


# Can be used anywhere to get the current logged in user.
# This will return None if the user is not logged in.
current_user = LocalProxy(lambda: getattr(_app_ctx_stack.top, 'user', None))


@app.before_request
def _load_user():
    """
    If the user is logged in, will place the user object on the
    application context.
    """
    user = None
    if 'uid' in session:
        user = r.hgetall('user:%d' % session['uid'])
    _app_ctx_stack.top.user = user


def get_uid_username(username):
    """
    Returns a user_id from username.
    """
    username = username.lower()
    uid = r.get('uid:username:%s' % username)
    if uid is not None:
        uid = int(uid)
    return uid


def get_uid_email(email):
    """
    Returns a user_id from email.
    """
    email = email.lower()
    uid = r.get('uid:email:%s' % email)
    if uid is not None:
        uid = int(uid)
    return uid


def get_uid(username):
    """
    Although the argument is called 'username' this will check for an e-mail
    and call the correct get_uid_* function.
    """
    if '@' in username:
        return get_uid_email(username)
    else:
        return get_uid_username(username)

def get_user(uid):
    """
    Similar to above but will return the user dict (calls above).
    """
    uid = int(uid)
    if uid:
        return r.hgetall('user:%d' % uid)
    else:
        return None


def get_email(uid):
    """
    Gets a users e-mail address from a uid
    """
    uid = int(uid)
    return r.hget('user:%d' % uid, 'email')


def check_username(username):
    """
    Used to check for username availability inside the signup form.
    Returns true if the name is free, false otherwise
    """
    username = username.lower()
    taken = username in reserved_names
    if not taken:
        taken = r.exists('uid:username:%s' % username)
    return False if taken else True


def check_email(email):
    """
    Used to check an e-mail addresses availability.
    Return true if free and false otherwise.
    """
    email = email.lower()
    if email_re.match(email):
        check = r.exists('uid:email:%s' % email)
        return True if not check else False
    return False


def create_user(username, email, password):
    """
    Creates a user account.
    """
    if check_username(username) and check_email(email):
        # Everything should be lowercase for lookups
        username = username.lower()
        email = email.lower()
        # Get new uid
        uid = int(r.incr('global:uid'))
        # Create user dictionary ready for HMSET
        user = {
            'uid': uid,
            'username': username,
            'email': email,
            'password': generate_password_hash(password),
            'created': timegm(gmtime()),
            'last_login': -1,
            'active': 0,
            'banned': 0,
            'op': 0,
            'about': "",
            'score': 0
        }
        # Transactional
        pipe = r.pipeline()
        pipe.hmset('user:%d' % uid, user)
        # Create look up keys for auth system (these are lowercase)
        pipe.set('uid:username:%s' % username, uid)
        pipe.set('uid:email:%s' % email, uid)
        pipe.execute()
        return uid
    return None


def is_active(uid):
    """
    Checks to see if a user account has been activated
    """
    uid = int(uid)
    return int(r.hget("user:%s" % uid, "active"))


def is_banned(uid):
    """
    Checks to see if a user account has been banned
    """
    uid = int(uid)
    return int(r.hget("user:%d" % uid, "banned"))


def authenticate(username, password):
    """
    Will authenticate a username/password combination.
    If successful will return a uid else will return None.
    """
    uid = get_uid(username)
    if uid and check_password_hash(r.hget('user:%d' % uid, 'password'), password):
        return uid
    return None


def login(uid):
    """
    Logs the user in. Will add user_id to session.
    Will also update the users last_login time.
    """
    session['uid'] = uid
    # update last login
    r.hset('user:%d' % uid, 'last_login', timegm(gmtime()))


def logout():
    """
    Removes the user id from the session. If it isn't there then
    nothing bad happens.
    """
    session.pop('uid', None)


def activate(uid):
    """
    Activates a user after signup
    """
    return r.hset('user:%d' % uid, 'active', 1)


def change_password(uid, password):
    """
    Changes uid's password. Checking of the old password _MUST_ be done before this.
    """
    password = generate_password_hash(password)
    return r.hset('user:%d' % uid, 'password', password)


def change_email(uid, email):
    """
    Changes the user with uid's e-mail address.
    Has to remove old lookup index and add the new one
    """
    pipe = r.pipeline()
    old_email = pipe.hget('user:%d' % uid, 'email')
    pipe.rem('uid:email:%s' % old_email)
    pipe.set('uid:email:%s' % email, uid)
    pipe.hset('user:%d' % uid, 'email', email)
    pipe.execute()
    return True


def is_safe_url(target):
    """
    Ensure the url is safe to redirect (this is here as auth==security)
    """
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
           ref_url.netloc == test_url.netloc


def generate_token(signer, data):
    """
    Generates a token using the signer passed in.
    """
    try:
        token = b64encode(signer.dumps(data).encode('ascii'))
        if app.config['DEBUG']:
            # Print the token to stderr in DEBUG mode
            print timegm(gmtime()), "Token generated:", token
    except (TypeError, ValueError):
        return None
    return token


def check_token(signer, token):
    """
    Checks a token against the passed in signer.
    If it fails returns None if it works the data from the
    original token will me passed back.
    """
    try:
        data = signer.loads(b64decode(token.encode('ascii')), max_age=86400)
        if app.config['DEBUG']:
            print timegm(gmtime()), "Token checked:", token
    except (TypeError, ValueError):
        return None
    return data