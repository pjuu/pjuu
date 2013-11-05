# 3rd party imports
from flask.ext.wtf import Form
from wtforms import PasswordField, TextField, ValidationError
from wtforms.validators import Email, EqualTo, Length, Regexp, Required

# Pjuu imports
from pjuu import db
from pjuu.users.models import User

# Package imports
from .backend import check_username


class ForgotForm(Form):
    username = TextField('User name or E-Mail')


class LoginForm(Form):
    username = TextField('User name or E-Mail')
    password = PasswordField('Password')


class ResetForm(Form):
    password = PasswordField('Password', [
        EqualTo('password2', message='Passwords must match'),
        Length(min=6,
               message='Password must be atleast 6 characters long'),
        Required()])
    password2 = PasswordField('Confirm password')


class PasswordChangeForm(Form):
    password = PasswordField('Password')
    new_password = PasswordField('New password', [
        EqualTo('new_password2', message='Passwords must match'),
        Length(min=6,
               message='Password must be atleast 6 characters long'),
        Required()])
    new_password2 = PasswordField('Confirm new password')


class EmailChangeForm(Form):
    password = PasswordField('Password')
    new_email = TextField('New e-mail address', [Email(),
                          Length(max=254), Required()])

    def validate_email(form, field):
        email = field.data.lower()
        user = user.query.filter(db.func.lower(email) == email).first()
        if user is not None:
            raise ValidationError('E-Mail address already in use')


class SignupForm(Form):
    username = TextField('User name', [
        Regexp(r'^[a-zA-Z0-9_]{3,16}$', message=('Username must be between 3 '
               'and 16 characters and can only contain '
               'lettrs, numbers and \'_\' characters.')),
        Required()])
    email = TextField('E-mail address', [Email(), Length(max=254), Required()])
    password = PasswordField('Password', [
        EqualTo('password2', message='Passwords must match'),
        Length(min=6,
               message='Password must be atleast 6 characters long'),
        Required()])
    password2 = PasswordField('Confirm password')

    def validate_username(form, field):
        check = check_username(field.data)
        if not check:
            raise ValidationError('User name already in use')

    def validate_email(form, field):
        email = field.data.lower()
        user = User.query.filter(db.func.lower(User.email == email)).first()
        if user is not None:
            raise ValidationError('E-mail address already in use')


class DeleteAccountForm(Form):
    password = PasswordField('Password')
