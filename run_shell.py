#!/usr/bin/env python
# -*- coding: utf8 -*-

"""
Description:
    Runs the Python shell with some initialisation actions performed to make
    it easier.

    The initialisation is very simple. An app is created as '_app' and an
    application context is created as '_ctx'

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
import code
# Pjuu imports
from pjuu import create_app


if __name__ == '__main__':
    """
    Starts the Python interpreter but before anything can be typed in
    will initialise the application and an app context
    """
    # Create app
    _app = create_app()
    # Create app_context
    _ctx = _app.app_context()
    # Push the context
    _ctx.push()

    # Print some information
    print 'Pjuu shell, app created at \'_app\', ' \
          'context created at \'_ctx\' and pushed'

    # Use Pjuu from the command line without all the overhead of having to do
    # the above
    code.interact()

    # Not sure if this will ever be called, but lets be precise
    _ctx.pop()
