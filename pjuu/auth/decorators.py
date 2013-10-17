# 3rd party imports
from functools import wraps
from flask import redirect, request, url_for, flash

# Package imports
from .backend import current_user


def anonymous_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if current_user:
            return redirect(url_for('feed'))
        return func(*args, **kwargs)    
    return decorated_view


def login_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not current_user:
            flash('You need to be logged in', 'info')
            return redirect(url_for('signin', next=request.path))
        return func(*args, **kwargs)
    return decorated_view
