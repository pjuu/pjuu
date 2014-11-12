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
from bson import ObjectId
from flask import current_app as app, _app_ctx_stack, session, g
from pymongo.errors import DuplicateKeyError
from werkzeug.security import (generate_password_hash as generate_password,
                               check_password_hash as check_password)
# Pjuu imports
from pjuu import mongo as m, redis as r
from pjuu.lib import keys as K, timestamp


# Username & E-mail checker re patterns
USERNAME_PATTERN = r'^\w{3,16}$'
EMAIL_PATTERN = r'^[^@%!/|`#&?]+@[^.@%!/|`#&?][^@%!/|`#&?]*\.[a-z]{2,10}$'
# Usuable regular expression objects
USERNAME_RE = re.compile(USERNAME_PATTERN)
EMAIL_RE = re.compile(EMAIL_PATTERN)


# TODO: Come up with a better solution for this.
# Reserved names
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
    'ihasalerts', 'i-has-alerts', 'hasalerts', 'has-alerts', 'report', 'terms',
    'privacy', 'aboutus', 'about_us', 'privacypolicy', 'privacy_policy',
    'termsandconditions', 'termsofservice', 'terms_and_conditions',
    'terms_of_service', 'alert']


@app.before_request
def _load_user():
    """Get the currently logged in user as a `dict` and store on the
    application context. This will be `None` if the user is not logged in.

    """
    user = None
    if 'uid' in session:
        # Fetch the user object from MongoDB
        user = m.db.users.find_one({'_id': session.get('uid')})
        # Remove the uid from the session if the user is not logged in
        if not user:
            session.pop('uid', None)
    _app_ctx_stack.top.user = user


@app.after_request
def inject_token_header(response):
    """During testing will add an HTTP header (X-Pjuu-Token) containing any
    auth tokens so that we can test these from the frontend tests. Checks
    `g.token` for the token to add.

    """
    # This only works in testing mode! Never allow this to happen on the site.
    # We won't check this with 'branch' as it won't ever branch the other way
    # or we atleast don't want it too.
    if app.testing:  # pragma: no branch
        token = g.get('token')
        if token:
            response.headers['X-Pjuu-Token'] = token
    return response


def create_user(username, email, password):
    """Creates a new user account.

    :param username: The new users user name
    :type username: str
    :param email: The new users e-mail address
    :type email: str
    :param password: The new users password un-hashed
    :type password: str
    :returns: The UID of the new user
    :rtype: ObjectId or None

    """
    try:
        # Create a new BSON ObjectId
        uid = str(ObjectId())

        user = {
            '_id': ObjectId(uid),
            'username': username.lower(),
            'email': email.lower(),
            'password': generate_password(password),
            'created': timestamp(),
            'last_login': -1,
            'active': False,
            'banned': False,
            'op': False,
            'muted': False,
            'about': "",
            'score': 0,
            'alerts_last_checked': -1,
        }

        # Insert the new user in to Mongo. If this fails a None will be
        # returned otherwise the string repr of the ObjectId uid
        return uid if m.db.users.insert(user) else None
    except DuplicateKeyError:
        # Oh no something went wrong. Pass over it. A None will be returned.
        pass

    return None


def get_uid_username(username):
    """Get the uid for user with username.

    :param username: The username to lookup
    :type username: str
    :returns: The users UID
    :rtype: ObjectId or None

    """
    # Look up the username inside mongo. The empty selector means that only the
    # _id will be returned which is what we want
    uid = m.db.users.find_one({'username': username.lower()}, {})

    # Check that something was returned
    if uid is not None:
        # Return the get. If the _id is not there for some reasons it means
        # that a None will still be returned
        return uid.get('_id')

    return None


def get_uid_email(email):
    """Get the uid for user with email.

    :param username: The email to lookup
    :type username: str
    :returns: The users UID
    :rtype: ObjectId or None

    """
    # Look up the email inside mongo
    uid = m.db.users.find_one({'email': email.lower()}, {})

    if uid is not None:
        return uid.get('_id')

    return None


def get_uid(lookup_value):
    """Calls either `get_uid_username` or `get_uid_email` depending on the
    the contents of `lookup_value`.

    :param lookup_value: The value to lookup
    :type lookup_value: str
    :returns: The users UID
    :rtype: ObjectId or None

    """
    if '@' in lookup_value:
        return get_uid_email(lookup_value)
    else:
        return get_uid_username(lookup_value)


def get_user(uid):
    """Get user with UID as `dict`.

    :param uid: The UID to get
    :type uid: str
    :returns: The user as a dict
    :rtype: dict or None

    """
    return m.db.users.find_one({'_id': uid})


def check_username_pattern(username):
    """Check that username matches what we class as a username

    :param username: The username to test the pattern of
    :type username: str
    :returns: True if successful match, False otherwise
    :rtype: bool

    """
    # Check the username is valid
    return bool(USERNAME_RE.match(username.lower()))


def check_username(username):
    """Check for username availability

    :param username: The username to check for existance
    :type username: str
    :returns: True is the username does NOT exist, False otherwise
    :rtype: bool

    """
    return username not in RESERVED_NAMES and \
        not bool(m.db.users.find({'username': username.lower()}, {}))


def check_email_pattern(email):
    """Checks that email matcheds what we class as an email address

    :param email: The email to test the pattern of
    :type email: str
    :returns: True if successful match, False otherwise
    :rtype: bool

    """
    return bool(EMAIL_RE.match(email.lower()))


def check_email(email):
    """Check an e-mail addresses availability

    :param email: The email to check for existance
    :type email: str
    :returns: True is the email does NOT exist, False otherwise
    :rtype: bool

    """
    return not bool(m.db.users.find_one({'email': email.lower()}, {}))


def user_exists(uid):
    """Helper function to check that a user exists or not.

    """
    return bool(m.db.users.find_one({'_id': uid}, {}))


def authenticate(username, password):
    """Authenticate a username/password combination.

    """
    result = m.db.users.find_one({'username': username})

    # Check that we got a result and that the password matches the stored one
    if result and check_password(result.get('password'), password):
        # If it matched return the document
        return result

    # Oh no, something went wrong
    return None


def login(uid):
    """Logs the user with uid in by adding the uid to the session.

    """
    session['uid'] = uid
    # update last login
    m.db.users.update({'_id': uid}, {'$set': {'last_login': timestamp()}})


def logout():
    """Removes the user id from the session.

    """
    session.pop('uid', None)


def activate(uid, action=True):
    """Activates a user account.

    """
    return m.db.users.update({'_id': ObjectId(uid)},
                             {'$set': {'active': action}})


def ban(uid, action=True):
    """ READ/WRITE
    Ban a user.

    By passing False as action this will unban the user
    """
    return m.db.users.update({'_id': uid}, {'$set': {'banned': action}})


def bite(uid, action=True):
    """ READ/WRITE
    Bite a user (think spideman), makes them op

    By passing False as action this will unbite the user
    """
    return m.db.users.update({'_id': uid}, {'$set': {'op': action}})


def mute(uid, action=True):
    """ READ/WRITE
    Mutes a user, this stops them from posting, commenting or following users

    By passing False as action this will un-mute the user
    """
    return m.db.users.update({'_id': uid}, {'$set': {'muted': action}})


def change_password(uid, password):
    """ Changes uid's password.

    Checking of the old password _MUST_ be done before you run this! This is a
    an unsafe function.

    """
    password = generate_password(password)
    return m.db.users.update({'_id': uid}, {'$set': {'password': password}})


def change_email(uid, new_email):
    """Changes the user with uid's e-mail address.

    Clears the old email key so that it can't be used and sets it to expire.

    """
    new_email = new_email.lower()
    return m.db.users.update({'_id': uid}, {'$set': {'email': new_email}})


def delete_account(uid):
    """Will delete a users account.

    This _MUST_ _REMOVE_ _ALL_ details, comments, posts, etc.

    Note: Ensure the user has authenticated this request.
          This is going to be the most _expensive_ task in Pjuu, be warned.

    """
    # Delete the user from MongoDB
    m.db.users.remove({'_id': uid})

    # Remove all posts a user has ever made. This includes all votes
    # on the posts and all comments of the posts.
    posts_cursor = m.db.posts.find({'uid': uid})
    for post in posts_cursor:
        # Get the posts id
        pid = post.get('_id')

        # Delete the Redis stuff
        # Delete all the votes made on the post
        r.delete(K.POST_VOTES.format(pid))
        # Delete posts subscribers list
        r.delete(K.POST_SUBSCRIBERS.format(pid))

        comments_cursor = m.db.comments.find({'pid': pid})
        for comment in comments_cursor:
            # Get the comments id
            cid = comment.get('_id')
            # Delete comment votes
            r.delete(K.COMMENT_VOTES.format(cid))
            # Delete the comment itself
            m.db.comments.remove({'_id': cid})

        # Delete the post itself
        m.db.posts.remove({'_id': pid})

    # Delete all comments the user has ever made
    m.db.comments.remove({'uid': uid})

    # Remove all the following relationships from Redis

    # Delete all references to followers of the user.
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

    # Delete the users feed, this may have been added too during this process.
    # Probably not but let's be on the safe side
    r.delete(K.USER_FEED.format(uid))

    # Delete the users alert list
    # DO NOT DELETE ANY ALERTS AS THESE ARE GENERIC
    r.delete(K.USER_ALERTS.format(uid))

    # All done. This code may need making SAFER in case there are issues
    # elsewhere in the code base.


def dump_account(uid):
    """Dump a users entire account; details, posts and comments to a dict.

    This WILL dump everything about the user. There is SOME caveats to this.
    It will not list all voters on posts or comments as this is just meta data
    on the posts. It will also not show your PASSWORD HASH as this probably
    isn't a danger factor but lets not test that.

    Your followers and following lists will also not be shown as these IDs are
    related to a user which IS NOT the user dumping the data.

    This will not list all comments underneath a post as this IS NOT the users
    data either.

    At the moment this WILL just dump account, posts and comments. ALL you have
    not deleted.

    TODO This will need to become streaming or a background process one day.
         This will be incredibly resource intensive.

    """
    # Attempt to get the users account
    user = m.db.users.find_one({'_id': uid})
    if user:
        # We are going to remove the uid and the password hash as this may
        # lead to some security issues
        user['uid'] = '<UID>'
        user['password'] = '<PASSWORD HASH>'
    else:
        # If there is no user then we will just stop this here. The account has
        # gone, there is no data anyway
        return None

    # Place to store our posts
    posts = []
    # Mongo cursor for all of our posts
    posts_cursor = m.db.posts.find({'uid': uid}).sort('created', -1)

    for post in posts_cursor:
        # Hide the uid from the post. The pid is okay to add as this is part of
        # the URL anyway
        post['uid'] = '<UID>'
        posts.append(post)

    # Get a list of the users comments
    comments = []
    # Mongo cursor for all our comments
    comments_cursor = m.db.comments.find({'uid': uid}).sort('created', -1)
    for comment in comments_cursor:
        comment['uid'] = '<UID>'
        comments.append(comment)

    # Return the dict of the above, this will be turned in to JSON by the view
    return {
        'user': user,
        'posts': posts,
        'comments': comments
    }
