# -*- coding: utf8 -*-

"""A simple implementation of auth tokens.

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2020 Joe Doherty

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
    tid = sha1((str(urandom(32)) + data).encode('utf-8')).hexdigest()
    # Set the token to JSON pickle value and place a 24HR timeout
    r.setex(K.TOKEN.format(tid), K.EXPIRE_24HRS, data)

    # For testing if a token is generated add it as a HTTP Header for us to
    # check with the test client.
    # Only ever do this in testing mode
    if app.debug or app.testing:  # pragma: no branch
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
            result = data
        except (TypeError, ValueError):
            # There was a problem pulling the data out of Redis.
            result = None
        finally:
            if not preserve:
                # Delete the token if preserve is False
                r.delete(K.TOKEN.format(tid))
        return result

    # If we didn't get data in the first place no need to delete.
    return None
