# -*- coding: utf8 -*-
# 3rd party imports
from flask.ext.wtf import Form
from wtforms import TextAreaField
from wtforms.validators import Required, Length


class PostForm(Form):
    """
    This is the form used for Posts and Comments at the momment.
    """
    body = TextAreaField('Post', [Required(), Length(max=255,
               message='Posts can not be larger than 255 characters')])
