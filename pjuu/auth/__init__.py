# -*- coding: utf8 -*-

"""
Description:
    Pjuu's authentication module.

    This should handle everything to do with looking after a users account.
    This does not include following or posting but simply access to Pjuu and
    tools to manage the account.

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
from flask import _app_ctx_stack
from werkzeug.local import LocalProxy


# Can be used anywhere to get the current logged in user.
# This will return None if the user is not logged in.
current_user = LocalProxy(lambda: getattr(_app_ctx_stack.top, 'user', None))
