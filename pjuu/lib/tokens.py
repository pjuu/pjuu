# -*- coding: utf8 -*-

##############################################################################
# Copyright 2014 Joe Doherty <joe@pjuu.com>
#
# Pjuu is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Pjuu is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
##############################################################################

# Stdlib imports
from base64 import (urlsafe_b64encode as b64encode,
                    urlsafe_b64decode as b64decode)
# 3rd party imports
from itsdangerous import SignatureExpired, BadSignature
# Pjuu imports
from pjuu import app
from . import timestamp


def generate_token(signer, data):
    """
    Generates a token using the signer passed in.
    """
    try:
        token = b64encode(signer.dumps(data).encode('ascii'))
        if app.debug:
            print timestamp(), "Generate token:", token
    except (TypeError, ValueError):
        return None
    return token


def check_token(signer, token):
    """
    Checks a token against the passed in signer.
    If it fails returns None if it works the data from the
    original token will me passed back.
    """
    try:
        data = signer.loads(b64decode(token.encode('ascii')), max_age=86400)
        if app.debug:
            print timestamp(), "Check token:", token
    except (TypeError, ValueError, SignatureExpired, BadSignature):
        return None
    return data
