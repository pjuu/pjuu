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
from werkzeug.security import (generate_password_hash as generate_password,
                               check_password_hash as check_password)
# Pjuu imports
from pjuu import redis as r
from pjuu.lib import keys as K, lua as L, timestamp, get_uuid


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
# TODO Come up with a better solution for this.
# Before adding a name here ensure that no one is using it.
# Names here DO NOT have to watch the pattern for usernames as these may change
# in the future. We need to protect endpoints which we need and can not afford
# to give to users.
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
    'username', 'usage', 'video', 'videos', 'web', 'webmail', 'alerts',
    'ihasalerts', 'i-has-alerts', 'hasalerts', 'has-alerts']


@app.before_request
def _load_user():
    """ Get the currently logged in user as a `dict` and store on the
    application context. This will be `None` if the user is not logged in.

    """
    user = None
    if 'uid' in session:
        user = r.hgetall(K.USER.format(session['uid']))
        # Remove the uid from the session if the user is not logged in
        if not user:
            session.pop('uid', None)
    _app_ctx_stack.top.user = user


@app.after_request
def inject_token_header(response):
    """ During testing will add an HTTP header (X-Pjuu-Token) containing any
    auth tokens so that we can test these from the frontend tests. Checks
    `g.token` for the token to add.

    """
    if app.testing:
        token = g.get('token')
        if token:
            response.headers['X-Pjuu-Token'] = token
    return response


def get_uid_username(username):
    """ Get the uid for user with username.

    :param username: The username to lookup
    :type username: str
    :returns: The users UID
    :rtype: str or None

    """
    # Attempt to get a uid from Redis with a lowercase username
    uid = r.get(K.UID_USERNAME.format(username.lower()))

    # Check that something was returned and it was not our defined None value
    if uid is not None and uid != K.NIL_VALUE:
        return uid

    return None


def get_uid_email(email):
    """  Returns the uid for user with email address.

    :param username: The email to lookup
    :type username: str
    :returns: The users UID
    :rtype: str or None

    """
    # Attemp to get a uid from Redis with a lowercase email
    uid = r.get(K.UID_EMAIL.format(email.lower()))

    # Check that something was returned and it was not our defined None value
    if uid is not None and uid != K.NIL_VALUE:
        return uid

    return None


def get_uid(lookup_value):
    """ Calls either `get_uid_username` or `get_uid_email` depending on the
    the contents of `lookup_value`.

    :param lookup_value: The value to lookup
    :type lookup_value: str
    :returns: The users UID
    :rtype: str or None

    """
    if '@' in lookup_value:
        return get_uid_email(lookup_value)
    else:
        return get_uid_username(lookup_value)


def get_user(uid):
    """ Get user with UID as `dict`.

    :param uid: The UID to get
    :type uid: str
    :returns: The user as a dict
    :rtype: dict or None

    """
    result = r.hgetall(K.USER.format(uid))
    return result if result else None


def get_username(uid):
    """ READ
    Get a users username by there uid
    """
    return r.hget(K.USER.format(uid), 'username')


def get_email(uid):
    """ READ
    Gets a users e-mail address from a uid
    """
    return r.hget(K.USER.format(uid), 'email')


def check_username_pattern(username):
    """ N/A
    Used to check a username matches a REGEX pattern
    """
    # Check the username is valid
    return bool(USERNAME_RE.match(username.lower()))


def check_username(username):
    """ READ
    Used to check for username availability inside the signup form.
    Returns true if the name is free, false otherwise
    """
    username = username.lower()

    return username not in RESERVED_NAMES and \
        not r.exists(K.UID_USERNAME.format(username))


def check_email_pattern(email):
    """ N/A
    Used to check an e-mail addresses matches the REGEX pattern.
    """
    email = email.lower()

    # Check the email is valid
    return bool(EMAIL_RE.match(email))


def check_email(email):
    """ READ
    Used to check an e-mail addresses availability.
    Return true if free and false otherwise.
    """
    email = email.lower()

    return not r.exists(K.UID_EMAIL.format(email))


def user_exists(uid):
    """ READ
    Helper function to check that a user exists or not.
    """
    return r.exists(K.USER.format(uid))


def create_user(username, email, password):
    """ READ/WRITE
    Creates a user account
    """
    username = username.lower()
    email = email.lower()
    if check_username(username) and check_email(email) and \
       check_username_pattern(username) and check_email_pattern(email):
        # Create the user lookup keys. This LUA script ensures
        # that the name can not be taken at the same time causing a race
        # condition. This is also passed a UUID and will only return it if
        # successful
        uid = L.create_user(keys=[K.UID_USERNAME.format(username),
                                  K.UID_EMAIL.format(email)],
                            args=[get_uuid()])
        # Create user dictionary ready for HMSET only if uid is not None
        if uid is not None:
            user = {
                'uid': uid,
                'username': username,
                'email': email,
                'password': generate_password(password),
                'created': timestamp(),
                'last_login': -1,
                'active': 0,
                'banned': 0,
                'op': 0,
                'muted': 0,
                'about': "",
                'score': 0,
                'alerts_last_checked': 0
            }
            r.hmset(K.USER.format(uid), user)
            # Set the TTL for the user account
            r.expire(K.USER.format(uid), K.EXPIRE_24HRS)
            return uid

    # If none of this worked return nothing
    return None


def is_active(uid):
    """ READ
    Checks to see if a user account has been activated
    """
    # Catch the exception if Redis returns Nones
    try:
        result = int(r.hget(K.USER.format(uid), "active"))
        return bool(result)
    except (TypeError, ValueError):
        return False


def is_banned(uid):
    """ READ
    Checks to see if a user account has been banned
    """
    # Catch the exception if Redis returns Nones
    try:
        result = int(r.hget(K.USER.format(uid), "banned"))
        return bool(result)
    except (TypeError, ValueError):
        return False


def is_op(uid):
    """ READ
    Checks to see if a user account is over powered
    """
    # Catch the exception if Redis returns Nones
    try:
        result = int(r.hget(K.USER.format(uid), "op"))
        return bool(result)
    except (TypeError, ValueError):
        return False


def is_mute(uid):
    """ READ
    Checks to see if a user account has been muted
    """
    # Catch the exception if Redis returns Nones
    try:
        result = int(r.hget(K.USER.format(uid), "muted"))
        return bool(result)
    except (TypeError, ValueError):
        return False


def authenticate(username, password):
    """ READ
    Will authenticate a username/password combination.
    If successful will return a uid else will return None.
    """
    uid = get_uid(username)

    # Check there is a uid and it is not NIL_VALUE
    if uid is not None and uid != K.NIL_VALUE \
       and check_password(r.hget(K.USER.format(uid), 'password'), password):
        return uid

    return None


def login(uid):
    """ WRITE
    Logs the user in. Will add user_id to session.
    Will also update the users last_login time.
    """
    session['uid'] = uid
    # update last login
    r.hset(K.USER.format(uid), 'last_login', timestamp())


def logout():
    """ N/A
    Removes the user id from the session. If it isn't there then
    nothing bad happens.
    """
    session.pop('uid', None)


def activate(uid, action=True):
    """ READ/WRITE
    Activates a user after signup.

    We will check if the user exists before, otherwise this would consume the
    ID and creates a user hash with simply {'active':1}
    """
    try:
        if user_exists(uid):
            action = int(action)
            r.hset(K.USER.format(uid), 'active', action)
            # Remove the TTL on the user keys
            r.persist(K.USER.format(uid))
            r.persist(K.UID_USERNAME.format(get_username(uid)))
            r.persist(K.UID_EMAIL.format(get_email(uid)))
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
        if user_exists(uid):
            action = int(action)
            r.hset(K.USER.format(uid), 'banned', action)
            return True
        else:
            return False
    except (TypeError, ValueError):
        return False


def bite(uid, action=True):
    """ READ/WRITE
    Bite a user (think spideman), makes them op

    By passing False as action this will unbite the user
    """
    try:
        if user_exists(uid):
            action = int(action)
            r.hset(K.USER.format(uid), 'op', action)
            return True
        else:
            return False
    except (TypeError, ValueError):
        return False


def mute(uid, action=True):
    """ READ/WRITE
    Mutes a user, this stops them from posting, commenting or following users

    By passing False as action this will un-mute the user
    """
    try:
        if user_exists(uid):
            action = int(action)
            r.hset(K.USER.format(uid), 'muted', action)
            return True
        else:
            return False
    except (TypeError, ValueError):
        return False


def change_password(uid, password):
    """ WRITE
    Changes uid's password. Checking of the old password _MUST_ be done
    before this.
    """
    password = generate_password(password)
    return r.hset(K.USER.format(uid), 'password', password)


def change_email(uid, new_email):
    """ WRITE
    Changes the user with uid's e-mail address.
    Has to remove old lookup index and add the new one

    Note: You NEED to check the e-mails before this happens
    """
    new_email = new_email.lower()
    # Get the previous e-mail address for the user
    old_email = r.hget(K.USER.format(uid), 'email')

    # Pipeline this to the server
    pipe = r.pipeline()
    # Set the old e-mail key to None
    pipe.set(K.UID_EMAIL.format(old_email), K.NIL_VALUE)
    # Set the old ket to expire
    pipe.expire(K.UID_EMAIL.format(old_email), K.EXPIRE_SECONDS)
    # Create the new key
    pipe.set(K.UID_EMAIL.format(new_email), uid)
    # Set the user objects e-mail to the new e-mail
    pipe.hset(K.USER.format(uid), 'email', new_email)
    pipe.execute()

    return True


def delete_account(uid):
    """ READ/WRITE
    Will delete a users account. This should remove _ALL_ details,
    comments, posts.

    Ensure the user has authenticated this request. Backends don't care!

    This is going to be the most _expensive_ task in Pjuu. Be warned.
    """
    # Get some information from the hashes to delete lookup keys
    username = r.hget(K.USER.format(uid), 'username')
    email = r.hget(K.USER.format(uid), 'email')

    # Clear the users lookup keys and user account. These are not needed
    pipe = r.pipeline()
    # Delete lookup keys. This will stop the user being found or logging in
    pipe.set(K.UID_USERNAME.format(username), K.NIL_VALUE)
    pipe.expire(K.UID_USERNAME.format(username), K.EXPIRE_SECONDS)
    pipe.set(K.UID_EMAIL.format(email), K.NIL_VALUE)
    pipe.expire(K.UID_EMAIL.format(email), K.EXPIRE_SECONDS)

    # Delete user account
    pipe.delete(K.USER.format(uid))
    pipe.execute()

    # Remove all posts a user has ever made. This includes all votes
    # on that post and all comments.
    pids = r.lrange(K.USER_POSTS.format(uid), 0, -1)
    for pid in pids:
        # Delete post
        r.delete(K.POST.format(pid))
        # Delete all the votes made on the post
        r.delete(K.POST_VOTES.format(pid))
        # Delete posts subscribers list
        r.delete(K.POST_SUBSCRIBERS.format(pid))

        cids = r.lrange(K.POST_COMMENTS.format(pid), 0, -1)
        for cid in cids:
            # Get author, ensure uid is an int
            cid_author = r.hget(K.COMMENT.format(cid), 'uid')
            # Delete comment
            r.delete(K.COMMENT.format(cid))
            # Delete comment votes
            r.delete(K.COMMENT_VOTES.format(cid))
            # Remove the cid from users comment list
            # This may remove some of ours. This will just make deleting
            # a bit quicker
            r.lrem(K.USER_COMMENTS.format(cid_author), 0, cid)
        # Delete the comments list
        r.delete(K.POST_COMMENTS.format(pid))
    # Delete the users post list
    r.delete(K.USER_POSTS.format(uid))

    # Delete all comments the user has every made. Including all votes on
    # those comments
    # This is a stripped down version of above for post comments.
    # We are not going to clean the lists related to the posts, they will
    # self clean. We also do not need to clear the comments from the users
    # comments list as it will be getting deleted straight after

    cids = r.lrange(K.USER_COMMENTS.format(uid), 0, -1)
    for cid in cids:
        # Get author, ensure uid is an int
        cid_author = r.hget(K.COMMENT.format(cid), 'uid')
        # Delete comment
        r.delete(K.COMMENT.format(cid))
        # Delete comment votes
        r.delete(K.COMMENT_VOTES.format(cid))
    # Delete the comments list
    r.delete(K.USER_COMMENTS.format(uid))

    # Delete all references to followers of the the user.
    # This will remove the user from the other users following list

    fids = r.zrange(K.USER_FOLLOWERS.format(uid), 0, -1)

    for fid in fids:
        # Clear the followers following list of the uid
        r.zrem(K.USER_FOLLOWING.format(fid), uid)
    # Delete the followers list
    r.delete(K.USER_FOLLOWERS.format(uid))

    # Delete all references to the users the user is following
    # This will remove the user from the others users followers list

    fids = r.zrange(K.USER_FOLLOWING.format(uid), 0, -1)

    for fid in fids:
        # Clear the followers list of people uid is following
        r.zrem(K.USER_FOLLOWERS.format(fid), uid)
    # Delete the following list
    r.delete(K.USER_FOLLOWING.format(uid))

    # Finally delete the users feed, this may have been added too during this
    # process. Probably not but let's be on the safe side
    r.delete(K.USER_FEED.format(uid))

    # Delete the users alert list
    # DO NOT DELETE ANY ALERTS AS THESE ARE GENERIC
    r.delete(K.USER_ALERTS.format(uid))

    # All done. This code may need making safer in case there are issues
    # elsewhere in the code base


def dump_account(uid):
    """ READ
    Will dump ALL of the users data as a dictionary ready for JSONify in the
    front end :)

    This WILL dump everything about the user. There is SOME caveats to this.
    It will not list all voters on posts or comments as this is just meta data
    on the posts. It will also not show your PASSWORD HASH as this probably
    isn't a danger factor but lets not test that.

    Your followers and following lists will also not be shown as these IDs are
    related to a user which IS NOT the user dumping the data.

    This will not list all comments underneath a post as this IS NOT the users
    data either.

    At the moment this WILL just dump account, posts and comments. ALL you have
    not deleted
    """
    # Attempt to get the users account
    user = r.hgetall(K.USER.format(uid))
    if user:
        # We are going to remove the uid and the password hash as this may
        # lead to some security issues
        user['uid'] = '<UID>'
        user['password'] = '<PASSWORD HASH>'
        user['created'] = int(float(user['created']))
    else:
        # If there is no user then we will just stop this here. The account has
        # gone, there is no data anyway
        return None

    # Get the users posts, pid's are not secret they are in the URLs. We will
    # hide the UIDs however
    posts = []
    for pid in r.lrange(K.USER_POSTS.format(uid), 0, -1):
        post = r.hgetall(K.POST.format(pid))
        # Don't add a post that does not exist
        if post:
            post['uid'] = '<UID>'
            post['created'] = int(float(post['created']))
            posts.append(post)

    # Get a list of the users comments
    comments = []
    for cid in r.lrange(K.USER_COMMENTS.format(uid), 0, -1):
        comment = r.hgetall(K.COMMENT.format(cid))
        if comment:
            comment['uid'] = '<UID>'
            comment['created'] = int(float(comment['created']))
            comments.append(comment)

    # Return the dict of the above, this will be turned in to JSON by the view
    return {
        'user': user,
        'posts': posts,
        'comments': comments
    }
