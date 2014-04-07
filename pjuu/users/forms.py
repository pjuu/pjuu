# -*- coding: utf8 -*-
# 3rd party imports
from flask.ext.wtf import Form
from wtforms import TextAreaField, TextField
from wtforms.validators import Length, Required


class ChangeProfile(Form):
    """
    This is the form used to update your about information
    """
    about = TextAreaField('About', [Required(), Length(max=255,
               message='Your about can not be larger than 255 characters')])

class SearchForm(Form):
	"""
	"""
	query =  TextField("Query")