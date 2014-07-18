# -*- coding: utf8 -*-

"""
Description:
    The backend function for the auth system.

    If in the future we decice to replace Redis we can simply change all these
    funtions to use a new backend

Licence:
    Copyright 2014 Joe Doherty <joe@pjuu.com>

    Pjuu is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    Pjuu is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

# Stdlib imports
import re
# 3rd party imports
from flask import current_app as app, _app_ctx_stack, session, g
from itsdangerous import TimedSerializer
from werkzeug.security import generate_password_hash, check_password_hash
# Pjuu imports
from pjuu import redis as r
from pjuu.lib import keys as K, lua as L, timestamp


# Username & E-mail checker re patters
USERNAME_PATTERN = r'^\w{3,16}$'
EMAIL_PATTERN = r'^[^@%!/|`#&?]+@[^.@%!/|`#&?][^@%!/|`#&?]*\.[a-z]{2,10}$'
# Usuable regular expression objects
USERNAME_RE = re.compile(USERNAME_PATTERN)
EMAIL_RE = re.compile(EMAIL_PATTERN)


# Token signers, These work along with lib/tokens.py
SIGNER_ACTIVATE = TimedSerializer(app.config['TOKEN_KEY'],
                                  app.config['TOKEN_SALT_ACTIVATE'])
SIGNER_FORGOT = TimedSerializer(app.config['TOKEN_KEY'],
                                app.config['TOKEN_SALT_FORGOT'])
SIGNER_EMAIL = TimedSerializer(app.config['TOKEN_KEY'],
                               app.config['TOKEN_SALT_EMAIL'])


# Reserved names
# TODO Come up with a better solution for this. Before adding a name here
# ensure that no one is using it.
RESERVED_NAMES = [
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


@app.before_request
def _load_user():
    """ READ
    If the user is logged in, will place the user object on the
    application context.

    This is so pjuu.auth.current_user can work
    """
    user = None
    if 'uid' in session:
        user = r.hgetall(K.USER % session['uid'])
        # Remove the uid from the session if the user is not logged in
        if not user:
            session.pop('uid', None)
    _app_ctx_stack.top.user = user


@app.after_request
def inject_token_header(response):
    """ N/A
    This function will always be called after a response but will only have any
    affect in testing mode. This will inject a header called X-Pjuu-Token into
    the response.

    When a token is created and TESTING = True, the token will be stored on
    the g object. This function will check this and then add the header
    """
    if app.testing:
        token = g.get('token')
        if token:
            response.headers['X-Pjuu-Token'] = token
    return response


def get_uid_username(username):
    """ READ
    Returns a uid from username.

    Returns None if lookup key does not exist or is '-1'
    """
    username = username.lower()
    try:
        uid = int(r.get(K.UID_USERNAME % username))
    except (TypeError, ValueError):
        uid = None

    if uid is not None and uid > 0:
        return uid
    return None


def get_uid_email(email):
    """ READ
    Returns a uid from email.

    Returns None if lookup key does not exist or is '-1'
    """
    email = email.lower()
    try:
        uid = int(r.get(K.UID_EMAIL % email))
    except (TypeError, ValueError):
        uid = None

    if uid is not None and uid > 0:
        return uid
    return None


def get_uid(username):
    """ N/A
    Although the argument is called 'username' this will check for an e-mail
    and call the correct get_uid_* function.
    """
    if '@' in username:
        return get_uid_email(username)
    else:
        return get_uid_username(username)


def get_user(uid):
    """ READ
    Similar to above but will return the user dict.
    """
    uid = int(uid)
    if uid:
        result = r.hgetall(K.USER % uid)
        return result if result else None
    return None


def get_username(uid):
    """ READ
    Get a users username by there uid
    """
    uid = int(uid)
    return r.hget(K.USER % uid, 'username')


def get_email(uid):
    """ READ
    Gets a users e-mail address from a uid
    """
    uid = int(uid)
    # Will return None if does not exist
    return r.hget(K.USER % uid, 'email')


def check_username_pattern(username):
    """ N/A
    Used to check a username matches a REGEX pattern
    """
    username = username.lower()

    # Check the username is valud
    if not USERNAME_RE.match(username):
        return False

    return True


def check_username(username):
    """ READ
    Used to check for username availability inside the signup form.
    Returns true if the name is free, false otherwise
    """
    username = username.lower()

    # Check the username is not reserved
    if username in RESERVED_NAMES:
        return False

    # Check no one is using the username
    uid = r.exists(K.UID_USERNAME % username)
    if uid:
        return False

    return True


def check_email_pattern(email):
    """ N/A
    Used to check an e-mail addresses matches the REGEX pattern.
    """
    email = email.lower()

    # Check the email is actually a valid e-mail
    if not EMAIL_RE.match(email):
        return False

    # Email is correct
    return True


def check_email(email):
    """ READ
    Used to check an e-mail addresses availability.
    Return true if free and false otherwise.
    """
    email = email.lower()

    # Ensure no one is already using the email address
    # This will also catch emails which have been deleted in the
    # last seven days
    uid = r.exists(K.UID_EMAIL % email)
    if uid:
        return False

    # Email is free
    return True


def create_user(username, email, password):
    """ READ/WRITE
    Creates a user account
    """
    username = username.lower()
    email = email.lower()
    if check_username(username) and check_email(email) and \
       check_username_pattern(username) and check_email_pattern(email):
        # Create the user lookup keys and get the uid. This LUA script ensures
        # that the name can not be taken at the same time causing a race
        # condition
        uid = L.create_user(keys=[K.UID_USERNAME % username,
                                  K.UID_EMAIL % email])
        # Create user dictionary ready for HMSET only if uid is not None
        if uid is not None:
            user = {
                'uid': uid,
                'username': username,
                'email': email,
                'password': generate_password_hash(password),
                'created': timestamp(),
                'last_login': -1,
                'active': 0,
                'banned': 0,
                'op': 0,
                'about': "",
                'score': 0
            }
            r.hmset(K.USER % uid, user)
            # Set the TTL for the user account
            r.expire(K.USER % uid, K.EXPIRE_24HRS)
            return uid
    return None


def is_active(uid):
    """ READ
    Checks to see if a user account has been activated
    """
    try:
        uid = int(uid)
        result = int(r.hget(K.USER % uid, "active"))
        return bool(result)
    except (TypeError, ValueError):
        return False


def is_banned(uid):
    """ READ
    Checks to see if a user account has been banned
    """
    try:
        uid = int(uid)
        result = int(r.hget(K.USER % uid, "banned"))
        return bool(result)
    except (TypeError, ValueError):
        return False


def is_op(uid):
    """ READ
    Checks to see if a user account is over powered
    """
    try:
        uid = int(uid)
        result = int(r.hget(K.USER % uid, "op"))
        return bool(result)
    except (TypeError, ValueError):
        return False


def authenticate(username, password):
    """ READ
    Will authenticate a username/password combination.
    If successful will return a uid else will return None.
    """
    uid = get_uid(username)
    # Check there is a uid and it is not '-1' (deleted account)
    if uid is not None \
       and check_password_hash(r.hget(K.USER % uid, 'password'), password):
        return uid

    return None


def login(uid):
    """ WRITE
    Logs the user in. Will add user_id to session.
    Will also update the users last_login time.
    """
    session['uid'] = uid
    # update last login
    r.hset(K.USER % uid, 'last_login', timestamp())


def logout():
    """ N/A
    Removes the user id from the session. If it isn't there then
    nothing bad happens.
    """
    session.pop('uid', None)


def activate(uid, action=True):
    """ READ/WRITE
    Activates a user after signup.

    We will check if the user exists otherwise this consumes the ID and
    creates a user hash with simply {'active':1}
    """
    try:
        uid = int(uid)
        if r.exists(K.USER % uid):
            action = int(action)
            r.hset(K.USER % uid, 'active', action)
            # Remove the TTL on the user keys
            r.persist(K.USER % uid)
            r.persist(K.UID_USERNAME % get_username(uid))
            r.persist(K.UID_EMAIL % get_email(uid))
            return True
        else:
            return False
    except (TypeError, ValueError):
        return False


def ban(uid, action=True):
    """ READ/WRITE
    Ban a user.

    By passing False as action this will unban the user
    """
    try:
        uid = int(uid)
        if r.exists(K.USER % uid):
            action = int(action)
            r.hset(K.USER % uid, 'banned', action)
            return True
        else:
            return False
    except (TypeError, ValueError):
        return False


def bite(uid, action=True):
    """ READ/WRITE
    Bite a user (think spideman), makes them op

    By passing False as action this will unban the user
    """
    try:
        uid = int(uid)
        if r.exists(K.USER % uid):
            action = int(action)
            r.hset(K.USER % uid, 'op', action)
            return True
        else:
            return False
    except (TypeError, ValueError):
        return False


def change_password(uid, password):
    """ WRITE
    Changes uid's password. Checking of the old password _MUST_ be done
    before this.

    Can only be tested 'is not None'.
    """
    uid = int(uid)
    password = generate_password_hash(password)
    return r.hset(K.USER % uid, 'password', password)


def change_email(uid, email):
    """ WRITE
    Changes the user with uid's e-mail address.
    Has to remove old lookup index and add the new one
    """
    uid = int(uid)
    # Get the previous e-mail address for the user
    old_email = r.hget(K.USER % uid, 'email')
    pipe = r.pipeline()
    pipe.set(K.UID_EMAIL % old_email, -1)
    pipe.expire(K.UID_EMAIL % old_email, K.EXPIRE_SECONDS)
    pipe.set(K.UID_EMAIL % email, uid)
    pipe.hset(K.USER % uid, 'email', email)
    pipe.execute()
    return True


def delete_account(uid):
    """ READ/WRITE
    Will delete a users account. This should remove _ALL_ details,
    comments, posts.

    Ensure the user has authenticated this request. Backends don't care!

    This is going to be the most _expensive_ task in Pjuu. Be warned.
    """
    uid = int(uid)
    # Get some information from the hashes to delete lookup keys
    username = r.hget(K.USER % uid, 'username')
    email = r.hget(K.USER % uid, 'email')

    # Clear the users lookup keys and user account. These are not needed
    pipe = r.pipeline()
    # Delete lookup keys. This will stop the user being found or logging in
    pipe.set(K.UID_USERNAME % username, -1)
    pipe.expire(K.UID_USERNAME % username, K.EXPIRE_SECONDS)
    pipe.set(K.UID_EMAIL % email, -1)
    pipe.expire(K.UID_EMAIL % email, K.EXPIRE_SECONDS)

    # Delete user account
    pipe.delete(K.USER % uid)
    pipe.execute()

    # Remove all posts a user has ever made. This includes all votes
    # on that post and all comments.
    pids = r.lrange(K.USER_POSTS % uid, 0, -1)
    for pid in pids:
        pid = int(pid)
        # Delete post
        r.delete(K.POST % pid) # WRITE
        # Delete all the votes made on the post
        r.delete(K.POST_VOTES % pid) # WRITE

        cids = r.lrange(K.POST_COMMENTS % pid, 0, -1)
        for cid in cids:
            cid = int(cid)
            # Get author, ensure uid is an int
            cid_author = r.hget(K.COMMENT % cid, 'uid')
            cid_author = int(cid_author)
            # Delete comment
            r.delete(K.COMMENT % cid) # WRITE
            # Delete comment votes
            r.delete(K.COMMENT_VOTES % cid) # WRITE
            # Remove the cid from users comment list
            # This may remove some of ours. This will just make deleting
            # a bit quicker
            r.lrem(K.USER_COMMENTS % cid_author, 0, cid) # WRITE
        # Delete the comments list
        r.delete(K.POST_COMMENTS % pid) # WRITE
    # Delete the users post list
    r.delete(K.USER_POSTS % uid) # WRITE

    # Delete all comments the user has every made. Including all votes on
    # those comments
    # This is a stripped down version of above for post comments.
    # We are not going to clean the lists related to the posts, they will
    # self clean. We also do not need to clear the comments from the users
    # comments list as it will be getting deleted straight after

    cids = r.lrange(K.USER_COMMENTS % uid, 0, -1)
    for cid in cids:
        cid = int(cid)
        # Get author, ensure uid is an int
        cid_author = r.hget(K.COMMENT % cid, 'uid')
        # Delete comment
        r.delete(K.COMMENT % cid)
        # Delete comment votes
        r.delete(K.COMMENT_VOTES % cid)
    # Delete the comments list
    r.delete(K.USER_COMMENTS % uid)

    # Delete all references to followers of the the user.
    # This will remove the user from the other users following list

    fids = r.zrange(K.USER_FOLLOWERS % uid, 0, -1)

    for fid in fids:
        fid = int(fid)
        # Clear the followers following list of the uid
        r.zrem(K.USER_FOLLOWING % fid, uid)
    # Delete the followers list
    r.delete(K.USER_FOLLOWERS % uid)

    # Delete all references to the users the user is following
    # This will remove the user from the others users followers list

    fids = r.zrange(K.USER_FOLLOWING % uid, 0, -1)

    for fid in fids:
        fid = int(fid)
        # Clear the followers list of people uid is following
        r.zrem(K.USER_FOLLOWERS % fid, uid)
    # Delete the following list
    r.delete(K.USER_FOLLOWING % uid)

    # Finally delete the users feed, this may have been added too during this
    # process. Probably not but let's be on the safe side
    r.delete(K.USER_FEED % uid)

    # All done. This code may need making safer in case there are issues
    # elsewhere in the code base
