# -*- coding: utf8 -*-

"""Web forms

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2015 Joe Doherty

"""

# 3rd party imports
from flask_wtf import Form
from wtforms import TextAreaField
from wtforms.validators import DataRequired, Length
# Pjuu imports
from pjuu.posts.backend import MAX_POST_LENGTH


class PostForm(Form):
    """Handle the input from the web for posts and replies.

    """

    body = TextAreaField('Post', [
        DataRequired(),
        Length(max=MAX_POST_LENGTH,
               message='Posts can not be larger than '
                       '{} characters'.format(MAX_POST_LENGTH))
    ])
