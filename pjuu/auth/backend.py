# -*- coding: utf8 -*-

"""Simple auth functions with access to the databases for use in the views.

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2020 Joe Doherty

"""

# Stdlib imports
from datetime import datetime
import re
# 3rd party imports
from flask import session
from pymongo.errors import DuplicateKeyError
from werkzeug.security import (generate_password_hash as generate_password,
                               check_password_hash as check_password)
# Pjuu imports
from pjuu import mongo as m, redis as r
from pjuu.auth.utils import get_user
from pjuu.lib import keys as k, timestamp, get_uuid
from pjuu.lib.uploads import delete_upload
from pjuu.posts.backend import delete_post


# Username & E-mail checker re patterns
USERNAME_PATTERN = r'^\w{3,16}$'
EMAIL_PATTERN = r'^[^@%!/|`#&?]+@[^.@%!/|`#&?][^@%!/|`#&?]*\.[a-z]{2,10}$'
# Usable regular expression objects
USERNAME_RE = re.compile(USERNAME_PATTERN)
EMAIL_RE = re.compile(EMAIL_PATTERN)


# TODO: Come up with a better solution for this.
# Reserved names
# Before adding a name here ensure that no one is using it.
# Names here DO NOT have to watch the pattern for usernames as these may change
# in the future. We need to protect endpoints which we need and can not afford
# to give to users.
RESERVED_NAMES = [
    'about', 'about_us', 'aboutus', 'access', 'account', 'accounts',
    'activate', 'add', 'address', 'adm', 'admin', 'administration', 'ajax',
    'alert', 'alerts', 'analytics', 'api', 'app', 'apps', 'archive', 'auth',
    'authentication', 'avatar', 'billing', 'bin', 'blog', 'blogs', 'cache',
    'calendar', 'careers', 'cgi', 'chat', 'client', 'code', 'config',
    'connect', 'contact', 'contest', 'create', 'css', 'dashboard', 'data',
    'db', 'delete', 'design', 'dev', 'devel', 'dir', 'directory', 'doc',
    'docs', 'domain', 'download', 'downloads', 'downvote', 'ecommerce', 'edit',
    'editor', 'email', 'faq', 'favorite', 'feed', 'feedback', 'file', 'files',
    'find', 'flog', 'follow', 'followers', 'following', 'forgot', 'forum',
    'forums', 'group', 'groups', 'has-alerts', 'hasalerts', 'help', 'home',
    'homepage', 'host', 'hosting', 'hostname', 'hpg', 'html', 'http', 'httpd',
    'https', 'i-has-alerts', 'ihasalerts', 'image', 'images', 'imap', 'img',
    'index', 'info', 'information', 'invite', 'java', 'javascript', 'job',
    'jobs', 'js', 'list', 'lists', 'log', 'login', 'logout', 'logs', 'mail',
    'master', 'media', 'message', 'messages', 'name', 'net', 'network', 'new',
    'news', 'newsletter', 'nick', 'nickname', 'notes', 'order', 'orders',
    'page', 'pager', 'pages', 'password', 'photo', 'photos', 'php', 'pic',
    'pics', 'pjuu', 'plugin', 'plugins', 'post', 'posts', 'privacy',
    'privacy_policy', 'privacypolicy', 'profile', 'project', 'projects', 'pub',
    'public', 'random', 'recover', 'register', 'registration', 'report',
    'reset', 'root', 'rss', 'script', 'scripts', 'search', 'secure',
    'security', 'send', 'service', 'setting', 'settings', 'setup', 'signin',
    'signup', 'singout', 'site', 'sitemap', 'sites', 'ssh', 'stage', 'staging',
    'start', 'stat', 'static', 'stats', 'status', 'store', 'stores',
    'subdomain', 'subscribe', 'support', 'system', 'tablet', 'talk', 'task',
    'tasks', 'template', 'templatestest', 'terms', 'terms_and_conditions',
    'terms_of_service', 'termsandconditions', 'termsofservice', 'tests',
    'theme', 'themes', 'tmp', 'todo', 'tools', 'unfollow', 'update', 'upload',
    'upvote', 'url', 'usage', 'user', 'username', 'video', 'videos', 'web',
    'webmail']


def create_account(username, email, password):
    """Creates a new user account.

    :param username: The new users user name
    :type username: str
    :param email: The new users e-mail address
    :type email: str
    :param password: The new users password un-hashed
    :type password: str
    :returns: The UID of the new user
    :rtype: str or None

    """
    username = username.lower()
    email = email.lower()
    try:
        if check_username(username) and check_username_pattern(username) and \
                check_email(email) and check_email_pattern(email):
            # Get a new UUID for the user
            uid = get_uuid()

            user = {
                '_id': uid,
                'username': username.lower(),
                'email': email.lower(),
                'password': generate_password(password,
                                              method='pbkdf2:sha256:2000',
                                              salt_length=20),
                'created': timestamp(),
                'last_login': -1,
                'active': False,
                'banned': False,
                'op': False,
                'muted': False,
                'about': "",
                'score': 0,
                'alerts_last_checked': -1,
                # Set the TTL for a newly created user, this has to be Datetime
                # object for MongoDB to recognise it. This is removed on
                # activation.
                'ttl': datetime.utcnow()
            }

            # Set all the tips for new users
            for tip_name in k.VALID_TIP_NAMES:
                user['tip_{}'.format(tip_name)] = True

            # Insert the new user in to Mongo. If this fails a None will be
            # returned
            result = m.db.users.insert(user)
            return uid if result else None
    except DuplicateKeyError:  # pragma: no cover
        # Oh no something went wrong. Pass over it. A None will be returned.
        pass

    return None


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

    :param username: The username to check for existence
    :type username: str
    :returns: True is the username does NOT exist, False otherwise
    :rtype: bool

    """
    return username not in RESERVED_NAMES and \
        not bool(m.db.users.find_one({'username': username.lower()}, {}))


def check_email_pattern(email):
    """Checks that email matches what we class as an email address

    :param email: The email to test the pattern of
    :type email: str
    :returns: True if successful match, False otherwise
    :rtype: bool

    """
    return bool(EMAIL_RE.match(email.lower()))


def check_email(email):
    """Check an e-mail addresses availability

    :param email: The email to check for existence
    :type email: str
    :returns: True if the email does NOT exist, False otherwise
    :rtype: bool

    """
    return not bool(m.db.users.find_one({'email': email.lower()}, {}))


def user_exists(user_id):
    """Is there a user object with `user_id`?

    """
    return bool(m.db.users.find_one({'_id': user_id}, {}))


def authenticate(username, password):
    """Authenticate a username/password combination.

    """
    # Case-insensitive login
    username = username.lower()

    if '@' in username:
        user = m.db.users.find_one({'email': username})
    else:
        user = m.db.users.find_one({'username': username})

    # Check that we got a result and that the password matches the stored one
    if user and check_password(user.get('password'), password):
        # If it matched return the document
        return user

    # Oh no, something went wrong
    return None


def signin(user_id):
    """Logs the user with uid in by adding the uid to the session.

    """
    session['user_id'] = user_id
    # update last login
    m.db.users.update({'_id': user_id}, {'$set': {'last_login': timestamp()}})


def signout():
    """Removes the user id from the session.

    """
    session.pop('user_id', None)


def activate(user_id, action=True):
    """Activates a user account and removes 'ttl' key from Mongo

    """
    return m.db.users.update(
        {'_id': user_id},
        {'$set': {'active': action}, '$unset': {'ttl': None}}
    ).get('updatedExisting')


def ban(user_id, action=True):
    """Ban a user.

    By passing False as action this will unban the user
    """
    return m.db.users.update(
        {'_id': user_id},
        {'$set': {'banned': action}}
    ).get('updatedExisting')


def bite(user_id, action=True):
    """Bite a user (think spideman), makes them op

    By passing False as action this will unbite the user
    """
    return m.db.users.update(
        {'_id': user_id},
        {'$set': {'op': action}}
    ).get('updatedExisting')


def mute(user_id, action=True):
    """Mutes a user, this stops them from posting, commenting or following
    users.

    By passing False as action this will un-mute the user
    """
    return m.db.users.update(
        {'_id': user_id},
        {'$set': {'muted': action}}
    ).get('updatedExisting')


def change_password(user_id, password):
    """Changes user with ``user_id``s password.

    Checking of the old password MUST be done before you run this! This is a
    an unsafe function. You will also need to apply sanity (length etc.) checks
    outside this function.

    """
    # Create the password hash from the plain-text password
    password = generate_password(password,
                                 method='pbkdf2:sha256:2000',
                                 salt_length=20)

    return m.db.users.update({'_id': user_id},
                             {'$set': {'password': password}})


def change_email(user_id, new_email):
    """Changes the user with ``user_id``'s e-mail address.

    Please ensure that it is a valid e-mail address out side of this function.
    This function is unsafe and provides NO sanity checking.

    """
    return m.db.users.update({'_id': user_id},
                             {'$set': {'email': new_email.lower()}})


def delete_account(user_id):
    """Will delete a users account.

    This **REMOVES ALL** details, posts, replies, etc. Not votes though.

    .. note: Ensure the user has authenticated this request. This is going to
             be the most *expensive* task in Pjuu, be warned.

    :param user_id: The `user_id` of the user to delete
    :type user_id: str

    """
    # Get the user object we will need this to remove the avatar
    user = get_user(user_id)

    # Delete the user from MongoDB
    m.db.users.remove({'_id': user_id})

    # If the user has an avatar remove it
    if user.get('avatar'):
        delete_upload(user.get('avatar'))

    # Remove all posts a user has ever made. This includes all votes
    # on the posts and all comments of the posts.
    # This calls the backend function from posts to do the deed
    posts_cursor = m.db.posts.find({'user_id': user_id}, {})
    for post in posts_cursor:
        delete_post(post.get('_id'))

    # Remove all the following relationships from Redis

    # Delete all references to followers of the user.
    # This will remove the user from the other users following list

    # TODO Replace with ZSCAN
    follower_cursor = r.zrange(k.USER_FOLLOWERS.format(user_id), 0, -1)

    for follower_id in follower_cursor:
        # Clear the followers following list of the uid
        r.zrem(k.USER_FOLLOWING.format(follower_id), user_id)
    # Delete the followers list
    r.delete(k.USER_FOLLOWERS.format(user_id))

    # Delete all references to the users the user is following
    # This will remove the user from the others users followers list

    # TODO Replace with ZSCAN
    followee_cursor = r.zrange(k.USER_FOLLOWING.format(user_id), 0, -1)

    for followee_id in followee_cursor:
        # Clear the followers list of people uid is following
        r.zrem(k.USER_FOLLOWERS.format(followee_id), user_id)
    # Delete the following list
    r.delete(k.USER_FOLLOWING.format(user_id))

    # Delete the users feed, this may have been added too during this process.
    # Probably not but let's be on the safe side
    r.delete(k.USER_FEED.format(user_id))

    # Delete the users alert list
    # DO NOT DELETE ANY ALERTS AS THESE ARE GENERIC
    r.delete(k.USER_ALERTS.format(user_id))

    # All done. This code may need making SAFER in case there are issues
    # elsewhere in the code base.


def dump_account(user_id):
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

    .. note: This will need to become streaming or a background process one
             day. This will be incredibly resource intensive.
    """
    # Attempt to get the users account
    user = m.db.users.find_one({'_id': user_id})
    if user:
        # We are going to remove the uid and the password hash as this may
        # lead to some security issues
        user['_id'] = '<UID>'
        user['password'] = '<PASSWORD HASH>'
    else:
        # If there is no user then we will just stop this here. The account has
        # gone, there is no data anyway
        return None

    # Place to store our posts
    posts = []
    # Mongo cursor for all of our posts
    posts_cursor = m.db.posts.find({'user_id': user_id}).sort('created', -1)

    for post in posts_cursor:
        # Hide the uid from the post. The pid is okay to add as this is part of
        # the URL anyway
        post['user_id'] = '<UID>'

        # Clear the user_id's from mentions
        if post.get('mentions'):
            for i in range(len(post['mentions'])):
                post['mentions'][i]['user_id'] = '<UID>'
        posts.append(post)

    # Return the dict of the above, this will be turned in to JSON by the view
    return {
        'user': user,
        'posts': posts,
    }
