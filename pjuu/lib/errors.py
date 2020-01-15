# -*- coding: utf8 -*-

"""Error handlers

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2020 Joe Doherty

"""

from flask import render_template
from flask_wtf.csrf import CSRFError
from werkzeug.exceptions import HTTPException, InternalServerError


custom_error_messages = {
    403: 'You\'re not allowed to do that.',
    404: 'We can\'t find what you\'re looking for.',
    405: 'We won\'t do that. No matter how much you love us.',
    500: 'WTF have you done?... Only joking!<br/>'
         'This a serious issue and we are looking in to it now.'
}


def handle_error(error):
    """Generically handle error messages with custom messages"""
    # Handle exceptions that are not Internal Server Errors
    if not isinstance(error, HTTPException):
        error = InternalServerError()  # pragma: no cover

    error.custom_message = custom_error_messages.get(error.code,
                                                     error.description)
    return render_template('errors.html', error=error), error.code


def handle_csrf_error(_):  # pragma: no cover
    """Show a custom CSRF failure error

    .. note: CSRF is VERY hard to test programmatically.
    """
    error = {}
    error['code'] = 400
    error['name'] = 'Invalid security token'
    error['custom_message'] = (
        'You may not have refreshed the page in a while. '
        'This is the main cause of the issue. However if you came here from '
        'another site some one may be trying to make you perform an action on '
        'Pjuu. Be safe. For more details search CSRF for an explanation.'
    )
    return render_template('errors.html', error=error), 400


def register_errors(app):
    for error in [403, 404, 405, 500]:
        app.errorhandler(error)(handle_error)

    app.errorhandler(CSRFError)(handle_csrf_error)
    app.errorhandler(Exception)(handle_error)
