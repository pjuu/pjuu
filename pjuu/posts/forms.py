# -*- coding: utf8 -*-

"""Web forms

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2016 Joe Doherty

"""

# 3rd party imports
from flask_wtf import Form
from flask_wtf.file import FileAllowed, FileField
from wtforms import TextAreaField
from wtforms.validators import DataRequired, Length
# Pjuu imports
from pjuu.posts.backend import MAX_POST_LENGTH


class PostForm(Form):
    """Handle the input from the web for posts and replies.

    """

    body = TextAreaField('Post', [
        DataRequired('A message is required.'),
        Length(max=MAX_POST_LENGTH,
               message='Posts can not be larger than '
                       '{} characters'.format(MAX_POST_LENGTH))
    ])

    upload = FileField('Upload', [
        FileAllowed(['gif', 'jpg', 'jpeg', 'png'],
                    'Only "gif", "jpg", "jpeg" and "png" files are supported')
    ])
