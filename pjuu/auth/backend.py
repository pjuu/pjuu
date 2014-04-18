# -*- coding: utf8 -*-
# Stdlib imports
from base64 import (urlsafe_b64encode as b64encode,
                    urlsafe_b64decode as b64decode)
from time import gmtime
from calendar import timegm
import re
# 3rd party imports
from flask import _app_ctx_stack, session
from itsdangerous import TimedSerializer, SignatureExpired
from werkzeug.local import LocalProxy
from werkzeug.security import generate_password_hash, check_password_hash
# Pjuu imports
from pjuu import app, redis as r
from pjuu.lib.tasks import (delete_comments, delete_posts, delete_followers,
                            delete_following)


# E-mail checker
email_re = re.compile(r'^.+@[^.].*\.[a-z]{2,10}$')


# Reserved names
# TODO Come up with a better solution for this. Before adding a name here
# ensure that no one is using it.
reserved_names = [
    'about', 'access', 'account', 'activate', 'accounts', 'add', 'address',
    'adm', 'admin', 'administration', 'ajax', 'analytics', 'activate',
    'recover', 'forgot', 'api', 'app', 'apps', 'archive', 'auth',
    'authentication', 'avatar', 'bin', 'billing', 'blog', 'blogs', 'chat',
    'cache', 'calendar', 'careers', 'cgi', 'client', 'code', 'config',
    'connect', 'contact', 'contest', 'create', 'code', 'css', 'dashboard',
    'data', 'db', 'design', 'delete', 'dev', 'devel', 'dir', 'directory',
    'doc', 'docs', 'domain', 'download', 'downloads', 'downvote', 'edit',
    'editor', 'email', 'ecommerce', 'forum', 'forums', 'faq', 'favorite',
    'feed', 'feedback', 'flog', 'follow', 'followers', 'following', 'forgot',
    'file', 'files', 'find', 'group', 'groups', 'help', 'home', 'homepage',
    'host', 'hosting', 'hostname', 'html', 'http', 'httpd', 'https', 'hpg',
    'info', 'information', 'image', 'img', 'images', 'imap', 'index', 'invite',
    'java', 'javascript', 'job', 'jobs', 'js', 'log', 'login', 'logs',
    'logout', 'list', 'lists', 'mail', 'master', 'media', 'message',
    'messages', 'name', 'net', 'network', 'new', 'news', 'newsletter', 'nick',
    'nickname', 'notes', 'order', 'orders', 'page', 'pager', 'pages',
    'password', 'pic', 'pics', 'photo', 'photos', 'php', 'pjuu', 'plugin',
    'plugins', 'post', 'posts', 'profile', 'project', 'projects', 'pub',
    'public', 'random', 'register', 'registration', 'reset', 'root', 'rss',
    'script', 'scripts', 'search', 'secure', 'send', 'service', 'signup',
    'signin', 'singout', 'search', 'security', 'setting', 'settings', 'setup',
    'site', 'sites', 'sitemap', 'ssh', 'stage', 'staging', 'start',
    'subscribe', 'subdomain', 'support', 'stat', 'static', 'stats', 'status',
    'store', 'stores', 'system', 'tablet', 'template', 'templates' 'test',
    'tests', 'theme', 'themes', 'tmp', 'todo', 'task', 'tasks', 'tools',
    'talk', 'unfollow', 'update', 'upload', 'upvote', 'url', 'user',
    'username', 'usage', 'video', 'videos', 'web', 'webmail']


# Signers
activate_signer = TimedSerializer(app.config['TOKEN_KEY'],
                                  salt=app.config['SALT_ACTIVATE'])
forgot_signer = TimedSerializer(app.config['TOKEN_KEY'],
                                salt=app.config['SALT_FORGOT'])
email_signer = TimedSerializer(app.config['TOKEN_KEY'],
                               salt=app.config['SALT_EMAIL'])


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
    Returns a uid from username.
    """
    username = username.lower()
    uid = r.get('uid:username:%s' % username)
    if uid is not None and uid > 0:
        uid = int(uid)
    return uid


def get_uid_email(email):
    """
    Returns a uid from email.
    """
    email = email.lower()
    uid = r.get('uid:email:%s' % email)
    if uid is not None and uid > 0:
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
    Similar to above but will return the user dict.
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
        uid = r.get('uid:username:%s' % username)
        if uid is not None:
            taken = True
    return False if taken else True


def check_email(email):
    """
    Used to check an e-mail addresses availability.
    Return true if free and false otherwise.
    """
    email = email.lower()
    uid = r.get('uid:email:%s' % email)
    if uid is not None:
        return False
    return True


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
    if uid is not None and uid > 0 \
       and check_password_hash(r.hget('user:%d' % uid, 'password'), password):
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
    Changes uid's password. Checking of the old password _MUST_ be done
    before this.
    """
    uid = int(uid)
    password = generate_password_hash(password)
    return r.hset('user:%d' % uid, 'password', password)


def change_email(uid, email):
    """
    Changes the user with uid's e-mail address.
    Has to remove old lookup index and add the new one
    """
    uid = int(uid)
    # Get the previous e-mail address for the user
    old_email = r.hget('user:%d' % uid, 'email')
    pipe = r.pipeline()
    pipe.set('uid:email:%s' % old_email, -1)
    pipe.pexpire('uid:email:%s' % old_email, 604800000)
    pipe.set('uid:email:%s' % email, uid)
    pipe.hset('user:%d' % uid, 'email', email)
    pipe.execute()
    return True


def delete_account(uid):
    """
    Will delete a users account. This should remove _ALL_ details,
    comments, posts.

    Ensure the user has authenticated this request. Backends don't care!

    This is going to be the most _expensive_ task in Pjuu. Be warned.
    """
    uid = int(uid)
    # Get some information from the hashes to delete lookup keys
    username = r.hget('user:%d' % uid, 'username')
    email = r.hget('user:%d' % uid, 'email')
    # Lets get started removing this person
    # Delete user account
    r.delete("user:%d" % uid)
    # Delete feed
    r.delete("user:%d:feed" % uid)
    # Delete posts
    # This will remove all the users posts and the list used to store this.
    # The feeds these posts belong to are left to self clean
    delete_posts(uid)
    # Delete comments
    # This will remove all the users comments and the list used to store them.
    # The posts the comments are attached too are left to self clean
    delete_comments(uid)
    # Clear followers sets
    # At the moment these lists are left to self clean
    # The number will be out of sync if the followers list are not accessed
    delete_followers(uid)
    # Clear following sets
    # At the moment these lists are left to self clean
    # The number will be out of sync if the following list is not accessed
    delete_following(uid)
    # Set uid lookup keys to -1 and set an expire time on them
    r.set('uid:username:%s' % username, -1)
    r.expire('uid:username:%s' % username, app.config['EXPIRE_SECONDS'])
    r.set('uid:email:%s' % email, -1)
    r.expire('uid:email:%s' % username, app.config['EXPIRE_SECONDS'])
    return True


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
    except (TypeError, ValueError, SignatureExpired):
        return None
    return data
