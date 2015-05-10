# -*- coding: utf8 -*-

"""Error handlers

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2015 Joe Doherty

"""

from flask import render_template


custom_error_messages = {
    403: 'You\'re not allowed to do that',
    404: 'We can\'t find what you\'re looking for',
    405: 'We won\'t do that. No matter how much you love us',
    500: 'WTF have you done?... Only joking!<br/>'
         'This a serious issue and we are looking in to it now.'
}


def handle_error(error):
    """Generically handle error messages with custom messages"""
    error.custom_message = custom_error_messages.get(error.code,
                                                     error.description)
    return render_template('errors.html', error=error), error.code


def register_errors(app):
    for error in [403, 404, 405, 500]:
        app.error_handler_spec[None][error] = handle_error
