# -*- coding: utf8 -*-

"""Web forms for handling user input.

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2020 Joe Doherty

"""

# 3rd party imports
from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, ValidationError
from wtforms.validators import EqualTo, Length, Regexp, DataRequired

# Pjuu imports
from pjuu.auth import current_user
from pjuu.auth.backend import (check_email, check_username, authenticate,
                               EMAIL_PATTERN, USERNAME_PATTERN)


class ForgotForm(FlaskForm):
    """Form for when you have forgotten your password

    """
    username = StringField('User name or E-Mail', [
        DataRequired()
    ])


class SignInForm(FlaskForm):
    """Form to allow users to login

    """
    username = StringField('User name or E-Mail', [
        DataRequired()
    ])
    password = PasswordField('Password', [
        DataRequired()
    ])
    keep_signed_in = BooleanField('Keep me signed in')

    def validate_username(form, field):
        """Strip surrounding white space from user name. This can happen on
        certain devices.
        """
        field.data = field.data.strip()


class ResetForm(FlaskForm):
    """Form to reset your password.

    """
    password = PasswordField('Password', [
        EqualTo('password2', message='Passwords must match'),
        Length(min=6,
               message='Password must be at least 6 characters long'),
        DataRequired()
    ])
    password2 = PasswordField('Confirm password')


class ChangePasswordForm(FlaskForm):
    """Allow users to change their own password

    """
    password = PasswordField('Current password')
    new_password = PasswordField('New password', [
        EqualTo('new_password2', message='Passwords must match'),
        Length(min=6,
               message='Password must be at least 6 characters long'),
        DataRequired()
    ])
    new_password2 = PasswordField('Confirm new password')

    def validate_password(self, field):
        if not authenticate(current_user['username'], field.data):
            raise ValidationError('Invalid password')


class ChangeEmailForm(FlaskForm):
    """Allow users to change their own e-mail address

    """
    new_email = StringField('New e-mail address', [
        Regexp(EMAIL_PATTERN, message='Invalid email address'),
        Length(max=254),
        DataRequired()
    ])
    password = PasswordField('Current password')

    def validate_new_email(self, field):
        if not check_email(field.data):
            raise ValidationError('E-mail address already in use')

    def validate_password(self, field):
        if not authenticate(current_user['username'], field.data):
            raise ValidationError('Invalid password')


class SignUpForm(FlaskForm):
    """Allow users to signup.

    """
    username = StringField('User name', [
        Regexp(USERNAME_PATTERN,
               message=('Must be between 3 and 16 characters and can only '
                        'contain letters, numbers and \'_\' characters.')),
        DataRequired()
    ])
    email = StringField('E-mail address', [
        Regexp(EMAIL_PATTERN, message='Invalid email address'),
        Length(max=254),
        DataRequired()
    ])
    password = PasswordField('Password', [
        Length(min=6,
               message='Password must be at least 6 characters long'),
        DataRequired()
    ])

    def validate_username(self, field):
        if not check_username(field.data):
            raise ValidationError('User name already in use')

    def validate_email(self, field):
        if not check_email(field.data):
            raise ValidationError('E-mail address already in use')


class ConfirmPasswordForm(FlaskForm):
    """Allow users to delete their own account

    """
    password = PasswordField('Current password')
