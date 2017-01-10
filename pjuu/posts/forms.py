# -*- coding: utf8 -*-

"""Web forms

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2017 Joe Doherty

"""

# 3rd party imports
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed
from wtforms import TextAreaField, RadioField, ValidationError, FileField
# Pjuu imports
from pjuu.posts.backend import MAX_POST_LENGTH


class PostForm(FlaskForm):
    """Handle the input from the web for posts and replies."""
    body = TextAreaField('Post')

    upload = FileField('Upload', [
        FileAllowed(['gif', 'jpg', 'jpeg', 'png'],
                    'Only "gif", "jpg", "jpeg" and "png" files are supported'),
    ])

    permission = RadioField('Permission', choices=[
        ('0', 'Public'),
        ('1', 'Pjuu'),
        ('2', 'Approved')
    ], default=0)

    def validate_body(self, field):
        if len(field.data.strip()) == 0 and not self.upload.data:
            raise ValidationError('Sorry. A message or an image is required.')

        if len(field.data.replace('\r\n', '\n')) > MAX_POST_LENGTH:
            raise ValidationError('Oh no! Posts can not be larger than '
                                  '{} characters'.format(MAX_POST_LENGTH))
