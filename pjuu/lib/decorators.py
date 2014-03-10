# -*- coding: utf8 -*-
from flask import request, url_for
from pjuu.auth import is_safe_url, current_user

def handles_next(func):

    @wraps(func)
    def decorator(*args, **kwargs):
        redirect_url = request.values.get('next', None)
        if not redirect_url or not is_safe_url(redirect_url):
            return func(*args, **kwargs)
        return func(redirect_endpoint=redirect_url, *args, **kwargs)

    return decorator


def pagination(func):

    @wraps(func)
    def decorator(*args, **kwargs):
        page = request.values.get('page', None)
        return func(page, *args, **kwargs)

    return decorator