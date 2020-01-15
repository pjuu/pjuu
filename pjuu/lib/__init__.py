# -*- coding: utf8 -*-

"""Helpers and miscellaneous functions.

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2020 Joe Doherty

"""

# Stdlib imports
from time import time
from urllib.parse import urlparse, urljoin
from uuid import uuid1

from flask import request, flash


def is_safe_url(host_url, target):
    """Ensure the url is safe to redirect.

    """
    ref_url = urlparse(host_url)
    test_url = urlparse(urljoin(host_url, target))
    return (test_url.scheme in ('http', 'https') and
            ref_url.netloc == test_url.netloc)


def handle_next(request, default_url='/'):
    """Will handle passing next to an argument and ensure it is safe.

    """
    redirect_url = request.args.get('next', None)
    if not redirect_url or not is_safe_url(request.host_url, redirect_url):
        redirect_url = default_url
    return redirect_url


def timestamp():
    """Generate a timestamp.

    """
    return time()


def get_uuid():
    """Return a new hex representation of a UUID.

    """
    return uuid1().hex


def fix_url(url):
    """Fix a URL by ensuring at has a scheme."""
    _url = urlparse(url, scheme='http')
    if _url.netloc == '':
        url = 'http://' + url
        _url = urlparse(url, scheme='http')
    return _url.geturl()


def xflash(message, category='message'):
    """Will only flash the message if the request is NOT XHR"""
    if not request.is_xhr:
        flash(message, category)
