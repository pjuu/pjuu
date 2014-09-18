# -*- coding: utf8 -*-

"""
Description:
    Helpers for Pjuu.

    I couldn't think of a better name which describes what services this module
    provides.

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
from urlparse import urlparse, urljoin
from time import gmtime, clock
from calendar import timegm


def is_safe_url(host_url, target):
    """
    Ensure the url is safe to redirect
    """
    ref_url = urlparse(host_url)
    test_url = urlparse(urljoin(host_url, target))
    return (test_url.scheme in ('http', 'https') and
            ref_url.netloc == test_url.netloc)


def handle_next(request, default_url='/'):
    """
    Will handle passing next to an argument and ensure it is safe
    """
    redirect_url = request.args.get('next', None)
    if not redirect_url or not is_safe_url(request.host_url, redirect_url):
        redirect_url = default_url
    return redirect_url


def timestamp():
    """
    This function will generate a UNIX UTC + Clock timestamp integer.

    This is too be placed at all timestamped occurances.


    Note: gmtime (and time) are not accurate enough on there own for this.
          The system clock has been appended for additional accuracy.
    """
    return timegm(gmtime()) + clock()
