# -*- coding: utf8 -*-

"""
Description:
    The actual Flask endpoints for the auth system.

Licence:
    Copyright 2014 Joe Doherty <joe@pjuu.com>

    Pjuu is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    Pjuu is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

# 3rd party imports
from flask import (current_app as app, flash, redirect, render_template,
                   request, url_for, session, jsonify, Blueprint, g,
                   _app_ctx_stack)
# Pjuu imports
from pjuu.lib import handle_next
from pjuu.lib.mail import send_mail
from pjuu.lib.tokens import generate_token, check_token
from pjuu.auth import current_user
from pjuu.auth.backend import (authenticate, login, logout, create_user,
                               activate as be_activate, get_user, get_uid,
                               change_password as be_change_password,
                               change_email as be_change_email,
                               delete_account as be_delete_account,
                               dump_account as be_dump_account)
from pjuu.auth.decorators import anonymous_required, login_required
from pjuu.auth.forms import (ForgotForm, SignInForm, ResetForm, SignUpForm,
                             ChangeEmailForm, ChangePasswordForm,
                             ConfirmPasswordForm)


auth_bp = Blueprint('auth', __name__)


@auth_bp.before_app_request
def _load_user():
    """Get the currently logged in user as a `dict` and store on the
    application context. This will be `None` if the user is not logged in.

    """
    user = None
    if 'uid' in session:
        # Fetch the user object from MongoDB
        user = get_user(session.get('uid'))
        # Remove the uid from the session if the user is not logged in
        if not user:
            session.pop('uid', None)
    _app_ctx_stack.top.user = user


@auth_bp.before_app_request
def kick_banned_user():
    """
    This function will check too see if the user has been banned since login.

    Without this we would have to wait for the user to try and login again
    before they are informed that they are banned. This fucntion will just
    ensure they are kicked out
    """
    if current_user and current_user.get('banned', False):
        session.pop('uid', None)
        flash('You\'re a very naughty boy!', 'error')


@auth_bp.after_app_request
def inject_token_header(response):
    """During testing will add an HTTP header (X-Pjuu-Token) containing any
    auth tokens so that we can test these from the frontend tests. Checks
    `g.token` for the token to add.

    """
    # This only works in testing mode! Never allow this to happen on the site.
    # We won't check this with 'branch' as it won't ever branch the other way
    # or we atleast don't want it too.
    if app.testing:  # pragma: no branch
        token = g.get('token')
        if token:
            response.headers['X-Pjuu-Token'] = token
    return response


@auth_bp.app_context_processor
def inject_user():
    """
    Injects `current_user` into the Jinja environment
    """
    return dict(current_user=current_user)


@auth_bp.route('/signin', methods=['GET', 'POST'])
@anonymous_required
def signin():
    """Logs a user in.

    Will authenticate username/password, check account activation and
    if the user is banned or not before setting user_id in session.

    """
    form = SignInForm(request.form)
    if request.method == 'POST':
        # Handles the passing of the next argument to the login view
        redirect_url = handle_next(request, url_for('users.feed'))

        if form.validate():
            # Calls authenticate from backend.py
            user = authenticate(form.username.data, form.password.data)
            if user:
                # Ensure the user is active
                if not user.get('active', False):
                    flash('Please activate your account<br />'
                          'Check your e-mail', 'information')
                # Ensure the user is not banned
                elif user.get('banned', False):
                    flash('You\'re a very naughty boy!', 'error')
                # All OK log the user in
                else:
                    # We will also make the session permanent if the user
                    # has requested too
                    session.permanent = form.keep_signed_in.data
                    login(user.get('_id'))
                    return redirect(redirect_url)
            else:
                flash('Invalid user name or password', 'error')
        else:
            flash('Invalid user name or password', 'error')
    return render_template('signin.html', form=form)


@auth_bp.route('/signout', methods=['GET'])
def signout():
    """
    Logs a user out.
    This will always go to /signin regardless. If user was actually
    logged out it will let them know.
    """
    if current_user:
        logout()
        flash('Successfully signed out', 'success')
    return redirect(url_for('signin'))


@auth_bp.route('/signup', methods=['GET', 'POST'])
@anonymous_required
def signup():
    """
    The view a user uses to sign up for Pjuu.

    This will generate the activation email and send it to the new user so
    long as the form is correct.
    """
    form = SignUpForm(request.form)
    if request.method == 'POST':
        if form.validate():
            # User successfully signed up, create an account
            uid = create_user(form.username.data, form.email.data,
                              form.password.data)

            # Lets check the account was created
            # This would only fail in the event of a race condition
            if uid:  # pragma: no branch
                token = generate_token({'action': 'activate', 'uid': uid})
                # Send an e-mail to activate their account
                send_mail(
                    'Pjuu Account Notification - Activation',
                    [form.email.data],
                    text_body=render_template('emails/activate.txt',
                                              token=token),
                    html_body=render_template('emails/activate.html',
                                              token=token)
                )
                flash('Yay! You\'ve signed up<br/>Please check your e-mails '
                      'to activate your account', 'success')
                return redirect(url_for('signin'))

        flash('Oh no! There are errors in your form. Please try again.',
              'error')

    return render_template('signup.html', form=form)


@auth_bp.route('/activate/<token>', methods=['GET'])
@anonymous_required
def activate(token):
    """
    Activates the user account so long as the token is valid.
    """
    # Attempt to get the data from the token
    data = check_token(token)
    if data is not None and data.get('action') == 'activate':
        # Attempt to activate the users account
        user = get_user(data.get('uid'))
        # This does not need a branching check as it should never fail!
        # The check is there for safety. An auth token can not live longer
        # than a newly created user.
        if user is not None:  # pragma: no branch
            be_activate(user.get('_id'))
            # If we have got to this point. Send a welcome e-mail :)
            send_mail(
                'Pjuu Account Notifcation - Welcome!',
                [user.get('email')],
                text_body=render_template('emails/welcome.txt'),
                html_body=render_template('emails/welcome.html')
            )
            flash('Your account has now been activated', 'success')
            return redirect(url_for('signin'))

    # The token is either out of date or has been tampered with
    flash('Invalid token', 'error')
    return redirect(url_for('signin'))


@auth_bp.route('/forgot', methods=['GET', 'POST'])
@anonymous_required
def forgot():
    """
    View to allow the user to recover their password.

    This will send an email to the users email address so long as the account
    is found. It will not tell the user if the account was located or not.
    """
    form = ForgotForm(request.form)
    # We always go to /signin after a POST
    if request.method == 'POST':
        user = get_user(get_uid(form.username.data))
        if user is not None:
            # Only send e-mails to user which exist.
            token = generate_token({'action': 'reset', 'uid': user.get('_id')})
            send_mail(
                'Pjuu Account Notification - Password Reset',
                [user.get('email')],
                text_body=render_template('emails/forgot.txt',
                                          token=token),
                html_body=render_template('emails/forgot.html',
                                          token=token)
            )
        flash('If we\'ve found your account we\'ve e-mailed you',
              'information')
        return redirect(url_for('signin'))
    return render_template('forgot.html', form=form)


@auth_bp.route('/reset/<token>', methods=['GET', 'POST'])
@anonymous_required
def reset(token):
    """
    This view allows the user to create a new password so long as the token
    is valid.
    """
    form = ResetForm(request.form)

    # Check the token but do not delete it.
    data = check_token(token, preserve=True)

    if data is not None and data.get('action') == 'reset':
        if request.method == 'POST':
            if form.validate():
                # If the form was successful recheck the token but expire it.
                check_token(token)
                # Update the password and inform the users
                be_change_password(data['uid'], form.password.data)
                flash('Your password has now been reset', 'success')
                return redirect(url_for('signin'))
            else:
                flash('Oh no! There are errors in your form', 'error')
    else:
        flash('Invalid token', 'error')
        return redirect(url_for('signin'))
    return render_template('reset.html', form=form)


@auth_bp.route('/settings/email', methods=['GET', 'POST'])
@login_required
def change_email():
    """
    This view allows the user to change their their email address.

    It will send a token to the new address for the user to confirm they own
    it. The email will contain a link to confirm_email()
    """
    form = ChangeEmailForm(request.form)
    if request.method == 'POST':
        if form.validate():
            # User validates in the form
            # Get an authentication token
            token = generate_token({
                'action': 'change_email',
                'uid': current_user['_id'],
                'email': form.new_email.data}
            )
            # Send a confirmation to the new email address
            send_mail(
                'Pjuu Account Notification - Confirm Email Change',
                [form.new_email.data],
                text_body=render_template('emails/email_change.txt',
                                          token=token),
                html_body=render_template('emails/email_change.html',
                                          token=token)
            )
            flash('We\'ve sent you an email, please confirm this',
                  'success')
        else:
            flash('Oh no! There are errors in your form', 'error')

    return render_template('change_email.html', form=form)


@auth_bp.route('/settings/email/<token>', methods=['GET'])
@login_required
def confirm_email(token):
    """
    View to actually change the users password.

    This is the link they will sent during the email change procedure. If the
    token is valid the users password will be changed and a confirmation will
    be sent to the new email address.
    """
    # Attempt to get the data from the token
    data = check_token(token)
    if data is not None and data.get('action') == 'change_email':
        # Change the users e-mail
        uid = data.get('uid')
        # We will email the address stored in the token. This may help us
        # identify if there is any miss match
        email = data.get('email')
        # This could only happen if the user deletes there account then presses
        # the confirm email link that is sent to them.
        if uid and email:  # pragma: no branch
            be_change_email(uid, email)
            send_mail(
                'Pjuu Account Notification - Email Address Changed',
                [email],
                text_body=render_template('emails/confirm_email.txt'),
                html_body=render_template('emails/confirm_email.html')
            )
            flash('We\'ve updated your e-mail address', 'success')
            return redirect(url_for('change_email'))

    # The token is either out of date or has been tampered with
    flash('Invalid token', 'error')
    return redirect(url_for('change_email'))


@auth_bp.route('/settings/password', methods=['GET', 'POST'])
@login_required
def change_password():
    """
    The view a user uses to change their password.

    This will change their password straight away once they have authenticated,
    it will then send them a confirmation e-mail.
    """
    form = ChangePasswordForm(request.form)
    if request.method == 'POST':
        if form.validate():
            # User authenticates in the form
            # Update the users password!
            be_change_password(current_user['_id'], form.new_password.data)
            flash('We\'ve updated your password', 'success')
            # Inform the user via e-mail that their password has changed
            send_mail(
                'Pjuu Account Notification - Password Changed',
                [current_user['email']],
                text_body=render_template('emails/password_change.txt'),
                html_body=render_template('emails/password_change.html')
            )
        else:
            flash('Oh no! There are errors in your form', 'error')

    return render_template('change_password.html', form=form)


@auth_bp.route('/settings/delete', methods=['GET', 'POST'])
@login_required
def delete_account():
    """
    View the user uses to delete their account.

    Once the user has submitted the form and their password has been validated
    there is no turning back. They will receive an e-mail to confirm the
    account deletion.
    """
    form = ConfirmPasswordForm(request.form)
    if request.method == 'POST':
        if authenticate(current_user['username'], form.password.data):
            uid = current_user['_id']
            email = current_user['email']
            # Log the current user out
            logout()
            # Delete the account
            be_delete_account(uid)
            # Inform the user that the account has/is being deleted
            flash('Your account is being deleted<br />Thanks for using us',
                  'information')
            # Send the user their last ever email on Pjuu
            send_mail(
                'Pjuu Account Notification - Account Deletion',
                [email],
                text_body=render_template('emails/account_deletion.txt'),
                html_body=render_template('emails/account_deletion.html')
            )
            # Send user back to login
            return redirect(url_for('signin'))
        else:
            flash('Oops! wrong password', 'error')

    return render_template('delete_account.html', form=form)


@auth_bp.route('/settings/dump', methods=['GET', 'POST'])
@login_required
def dump_account():
    """
    """
    form = ConfirmPasswordForm(request.form)
    if request.method == 'POST':
        if authenticate(current_user['username'], form.password.data):
            # Dump the users account
            data = be_dump_account(current_user['_id'])
            # JSONify the data and display it to the user :) simple
            return jsonify(data)
        else:
            flash('Oops! wrong password', 'error')

    return render_template('dump_account.html', form=form)
