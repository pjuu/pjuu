# 3rd party imports
from flask.ext.wtf import Form
from wtforms import TextAreaField
from wtforms.validators import Required


class PostForm(Form):
    '''
    This is the form used for Posts and Comments at the momment.
    '''
    body = TextAreaField('Post', [Required()])
