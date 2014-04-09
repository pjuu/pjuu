# -*- coding: utf8 -*-
# 3rd party imports
from flask.ext.wtf import Form
from wtforms import TextAreaField, TextField
from wtforms.validators import Length, Required


class ChangeProfileForm(Form):
    """ This is the form used to update your about information """
    about = TextAreaField('About', [Required(), Length(max=255,
               message='Your about can not be larger than 255 characters')])


class SearchForm(Form):
	""" This form is really simple. It is here to keep all forms at WTFroms """
	query =  TextField("Query")