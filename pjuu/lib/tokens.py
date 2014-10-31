# -*- coding: utf8 -*-

"""
Description:
    Our implementation of auth tokens.

    These are incredibly simply they

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
from flask import current_app as app, g
from hashlib import sha1
import jsonpickle
from os import urandom
import re
# Pjuu imports
from pjuu import redis as r
import pjuu.lib.keys as K


TOKEN_RE = re.compile(r'[0-9a-f]+')


def generate_token(data):
    """Create a new auth token. Stores the data in Redis and returns a UUID.

    """
    # Convert the data to a JSON pickle, you can store anything you want.
    data = jsonpickle.encode(data)
    # Get our token id.
    tid = sha1(urandom(32) + data).hexdigest()
    # Set the token to JSON pickle value and place a 24HR timeout
    r.setex(K.TOKEN.format(tid), K.EXPIRE_24HRS, data)

    # For testing if a token is generated add it as a HTTP Header for us to
    # check with the test client.
    # Only ever do this in testing mode
    if app.testing:  # pragma: no branch
        g.token = tid

    return tid


def check_token(tid, preserve=False):
    """Look up token with tid and return the data which was stored or None.

    """
    # Stop malformed tokens making calls to Redis
    if not TOKEN_RE.match(tid):
        return None

    # Get the pickled data from Redis
    data = r.get(K.TOKEN.format(tid))

    if data:
        try:
            # Attempt to get the pickled object back
            data = jsonpickle.decode(data)
            return data
        except (TypeError, ValueError):
            # There was a problem pulling the data out of Redis.
            return None
        finally:
            # What the actual fuck coverage? It says this is a partial yet
            # there is a specific test for this. Must be something to do with
            # the finally block. The else is POINTLESS but works.
            if not preserve:
                # Delete the token if preserve is False
                r.delete(K.TOKEN.format(tid))
            else:
                pass

    # If we didn't get data in the first place no need to delete.
    return None
