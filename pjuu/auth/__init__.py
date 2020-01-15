# -*- coding: utf8 -*-

"""Provides authentication, anything that deals with the users account.

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2020 Joe Doherty

"""

# 3rd party imports
from flask import _app_ctx_stack
from werkzeug.local import LocalProxy


# Can be used anywhere to get the currently logged in user.
# This will return None if the user is not logged in.
current_user = LocalProxy(lambda: getattr(_app_ctx_stack.top, 'user', None))
