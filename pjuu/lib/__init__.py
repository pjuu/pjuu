# -*- coding: utf8 -*-
from urlparse import urlparse, urljoin


def is_safe_url(host_url, target):
    """
    Ensure the url is safe to redirect
    """
    ref_url = urlparse(host_url)
    test_url = urlparse(urljoin(host_url, target))
    return test_url.scheme in ('http', 'https') and \
           ref_url.netloc == test_url.netloc


def handle_next(request, default_url='/'):
    """
    Will handle passing next to an argument and ensure it is safe
    """
    redirect_url = request.values.get('next', None)
    if not redirect_url or not is_safe_url(request.host_url, redirect_url):
        redirect_url = default_url
    return redirect_url