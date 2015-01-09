# -*- coding: utf8 -*-

"""Auth utilities which are used across the code base and could cause possible
circular imports.

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2015 Joe Doherty

"""


from pjuu import mongo as m


def get_uid_username(username):
    """Find a uid given a username.

    :param username: The username to lookup
    :type username: str
    :returns: The users UID
    :rtype: str or None

    """
    # Will return the user object with on the _id (user_id) field
    user = m.db.users.find_one({'username': username.lower()}, {})

    if user is not None:
        return user.get('_id')

    return None


def get_uid_email(email):
    """Find a uid given a username.

    :param email: The email to lookup
    :type email: str
    :returns: The users UID
    :rtype: str or None

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
    :rtype: str or None

    """
    if '@' in lookup_value:
        return get_uid_email(lookup_value)
    else:
        return get_uid_username(lookup_value)


def get_user(user_id):
    """Get user with `user_id` as `dict`.

    :param user_id: The user_id to get
    :type user_id: str
    :returns: The user as a dict
    :rtype: dict or None

    """
    return m.db.users.find_one({'_id': user_id})