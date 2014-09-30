# -*- coding: utf8 -*-

"""
Description:
    Auth view dectorators

    These are used to limit access to the site if a user is not logged in and
    similarly stop users who are logged in from getting to various auth
    views.

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

# 3rd party imports
from functools import wraps
from flask import redirect, request, url_for, flash
# Pjuu imports
from pjuu.auth import current_user


def anonymous_required(func):
    """
    Will stop a user going to a page which requires a user to be
    logged out (login, signup, etc...)
    """
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if current_user:
            return redirect(url_for('feed'))
        return func(*args, **kwargs)

    return decorated_view


def login_required(func):
    """
    Will stop a user going to a page which requires a user to be
    logged in (feed, profile, etc...)
    """
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not current_user:
            flash('You need to be logged in to view that', 'information')
            return redirect(url_for('signin', next=request.path))
        return func(*args, **kwargs)

    return decorated_view
