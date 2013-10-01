# 3rd party imports
from flask.ext.wtf import Form
from flask_wtf import RecaptchaField
from wtforms import PasswordField, TextField, ValidationError
from wtforms.validators import Length, Regexp, Required


class PostForm(Form):
    '''
    This is the form used for Posts and Comments at the momment.
    '''
    body = TextField('Post',
            [Length(min=2, max=1024,
                    message='Posts can only be 1024 characters max')])
