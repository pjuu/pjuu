# -*- coding: utf8 -*-

"""Web forms

:license: AGPL v3, see LICENSE for more details
:copyright: Joe Doherty 2015

"""

# 3rd party imports
from flask_wtf import Form
from wtforms import TextAreaField
from wtforms.validators import DataRequired, Length


class PostForm(Form):
    """Handle the input from the web for posts and replies.

    """
    body = TextAreaField('Post', [
        DataRequired(),
        Length(max=255,
               message='Posts can not be larger than '
                       '{} characters'.format(255))
    ])
