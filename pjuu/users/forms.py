# -*- coding: utf8 -*-

"""Web forms.

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2020 Joe Doherty

"""

# 3rd party imports
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import (
    BooleanField, TextAreaField, SelectField, StringField, RadioField
)
from wtforms.validators import Length, Optional, Regexp
# Pjuu imports
from pjuu.posts.backend import MAX_POST_LENGTH
from pjuu.lib.parser import URL_RE


class ChangeProfileForm(FlaskForm):
    """This is the form used to update your about information"""
    upload = FileField('Upload', [
        FileAllowed(['gif', 'jpg', 'jpeg', 'png'],
                    'Only "gif", "jpg", "jpeg" and "png" files are supported')
    ])

    hide_feed_images = BooleanField('Hide images in feeds')

    choices = [('25', '25'), ('50', '50'), ('100', '100')]

    feed_pagination_size = SelectField('Number of feed items to show',
                                       choices=choices, default=25)
    replies_pagination_size = SelectField('Number of replies to show',
                                          choices=choices, default=25)
    alerts_pagination_size = SelectField('Number of alerts to show',
                                         choices=choices, default=50)

    reply_sort_order = BooleanField('Show replies in chronological order')

    homepage = StringField('Home page', [
        Regexp(URL_RE,
               message='Please ensure the home page is a valid URL or empty'),
        Optional()
    ])

    location = StringField('Location', [Optional()])

    about = TextAreaField('About', [
        Length(max=MAX_POST_LENGTH,
               message='About can not be larger than '
                       '{} characters'.format(MAX_POST_LENGTH))

    ])

    permission = RadioField('Permission', choices=[
        ('0', 'Public'),
        ('1', 'Pjuu'),
        ('2', 'Approved')
    ], default=0)


class SearchForm(FlaskForm):
    """
    This form is really simple. It is here to keep all forms at WTFroms
    """
    query = StringField("Query")
