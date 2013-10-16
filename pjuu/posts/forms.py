# 3rd party imports
from flask.ext.wtf import Form
from wtforms import IntegerField, TextAreaField
from wtforms.validators import Length


class PostForm(Form):
    '''
    This is the form used for Posts and Comments at the momment.
    '''
    body = TextAreaField('Post',
            [Length(min=2, max=512,
                    message='Posts can only be 512 characters max')])
