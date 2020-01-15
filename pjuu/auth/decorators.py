# -*- coding: utf8 -*-

"""Python decorators enforce permissions on the web views.

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2020 Joe Doherty

"""

# 3rd party imports
from functools import wraps
from flask import abort, redirect, request, url_for, flash
# Pjuu imports
from pjuu.auth import current_user


def anonymous_required(func):
    """Will stop a user going to a page which requires a user to be logged out

    """
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if current_user:
            return redirect(url_for('users.feed'))
        return func(*args, **kwargs)

    return decorated_view


def login_required(func):
    """Will stop a user going to a page which requires a user to be logged in

    """
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not current_user:
            if request.is_xhr:
                return abort(403)

            flash('You need to be signed in to view that', 'information')
            return redirect(url_for('auth.signin', next=request.path))
        return func(*args, **kwargs)

    return decorated_view
