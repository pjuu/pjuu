# -*- coding: utf8 -*-

# Copyright 2014 Joe Doherty <joe@pjuu.com>
#
# Pjuu is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Pjuu is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# 3rd party imports
from flask import (flash, redirect, render_template, request,
                   url_for)
# Pjuu imports
from pjuu import app
from pjuu.lib import handle_next
from pjuu.lib.mail import send_mail
from pjuu.auth.backend import delete_account as be_delete_account
from .backend import (authenticate, current_user, login,
                      logout, create_user, activate_signer, forgot_signer,
                      email_signer, generate_token, check_token,
                      activate as be_activate,
                      change_password as be_change_password,
                      change_email as be_change_email,
                      get_uid, is_active, is_banned, get_email)
from .decorators import anonymous_required, login_required
from .forms import (ForgotForm, LoginForm, ResetForm, SignupForm,
                    ChangeEmailForm, PasswordChangeForm, DeleteAccountForm)


@app.context_processor
def inject_user():
    """
    Injects `current_user` into the Jinja environment
    """
    return dict(current_user=current_user)


@app.route('/signin', methods=['GET', 'POST'])
@anonymous_required
def signin():
    """
    Logs a user in.
    Will authenticate username/password, check account activation and
    if the user is banned or not before setting user_id in session.
    """
    form = LoginForm(request.form)
    if request.method == 'POST':
        # Handles the passing of the next argument to the login view
        redirect_url = handle_next(request, url_for('feed'))

        if form.validate():
            # Calls authenticate from backend.py
            uid = authenticate(form.username.data, form.password.data)
            if uid:
                if not is_active(uid):
                    flash('Please activate your account<br />'
                          'Check your e-mail', 'information')
                elif is_banned(uid):
                    flash('You\'re a very naughty boy!', 'error')
                else:
                    login(uid)
                    return redirect(redirect_url)
            else:
                flash('Invalid user name or password', 'error')
        else:
            flash('Invalid user name or password', 'error')
    return render_template('signin.html', form=form)


@app.route('/signout', methods=['GET'])
def signout():
    """
    Logs a user out.
    This will always go to /signin regardless. If user was actually
    logged out it will let them know.
    """
    if current_user:
        logout()
        flash('Successfully logged out', 'success')
    return redirect(url_for('signin'))


@app.route('/signup', methods=['GET', 'POST'])
@anonymous_required
def signup():
    form = SignupForm(request.form)
    if request.method == 'POST':
        if form.validate():
            # User successfully signed up, create an account
            uid = create_user(form.username.data, form.email.data,
                              form.password.data)
            # Lets check the account was created
            if uid:
                token = generate_token(activate_signer,
                                       {'uid': uid})
                # Do not send e-mail if NOMAIL
                if not app.config['NOMAIL']:
                    send_mail('Activation', [form.email.data],
                              text_body=render_template('emails/activate.txt',
                                                        token=token),
                              html_body=render_template('emails/activate.html',
                                                        token=token))
                flash('Yay! You\'ve signed up.<br>Please check your e-mails '
                      'to activate your account.', 'success')
                return redirect(url_for('signin'))
        # This will fire if the form is invalid
        flash('Oh no! There are errors in your signup form.', 'error')
    return render_template('signup.html', form=form)


@app.route('/activate/<token>', methods=['GET'])
@anonymous_required
def activate(token):
    # Attempt to get the data from the token
    data = check_token(activate_signer, token)
    if data is not None:
        # Attempt to activate the users account
        uid = data['uid']
        if uid:
            be_activate(uid)
            # If we have got to this point. Send a welcome e-mail :)
            if not app.config['NOMAIL']:
                send_mail('Welcome', [get_email(uid)],
                          text_body=render_template('emails/welcome.txt'),
                          html_body=render_template('emails/welcome.html'))
            flash('Your account has now been activated.', 'success')
            return redirect(url_for('signin'))
    # The token is either out of date or has been tampered with
    flash('Invalid token.', 'error')
    return redirect(url_for('signup'))


@app.route('/forgot', methods=['GET', 'POST'])
@anonymous_required
def forgot():
    form = ForgotForm(request.form)
    # We always go to /signin after a POST
    if request.method == 'POST':
        uid = get_uid(form.username.data)
        if uid:
            # Only send e-mails to user which exist.
            token = generate_token(forgot_signer, {'uid': uid})
            if not app.config['NOMAIL']:
                send_mail('Password reset', get_email(uid),
                          text_body=render_template('emails/forgot.txt',
                                                    token=token),
                          html_body=render_template('emails/forgot.html',
                                                    token=token))
        flash('If we\'ve found you we\'ve e-mailed you a reset link too you.',
              'information')
        return redirect(url_for('signin'))
    return render_template('forgot.html', form=form)


@app.route('/reset/<token>', methods=['GET', 'POST'])
@anonymous_required
def reset(token):
    form = ResetForm(request.form)
    data = check_token(forgot_signer, token)
    if data is not None:
        if request.method == 'POST':
            if form.validate():
                be_change_password(data['uid'], form.password.data)
                flash('Your password has been set. Please login.', 'success')
                return redirect(url_for('signin'))
            else:
                flash('Oh no! There are errors in your re-set form.', 'error')
    else:
        flash('Invalid token.', 'error')
        return redirect(url_for('signin'))
    return render_template('reset.html', form=form)


# The following commands should be used when the user is logged in.
# These have nothing to do with templates. All of these have to redirect
# to users.settings_account view so that the template naming and layout make
# sense.
# TODO: ALL OF THE BELOW


@app.route('/settings/email', methods=['GET', 'POST'])
@login_required
def change_email():
    form = ChangeEmailForm(request.form)
    if request.method == 'POST':
        if form.validate():
            if authenticate(current_user['username'], form.password.data):
                token = generate_token(email_signer,
                            {'uid': current_user['uid'],
                             'email': form.new_email.data})

                if not app.config['NOMAIL']:
                    send_mail('Confirm e-mail change', [form.new_email.data],
                              text_body=render_template('emails/activate.txt',
                                                        token=token),
                              html_body=render_template('emails/activate.html',
                                                        token=token))

                flash('We\'ve sent you an email, please confirm this.',
                      'success')
        else:
            flash('Oh no! There are errors in your change email form.',
                  'error')
    return render_template('change_email.html', form=form)


@app.route('/settings/email/<token>', methods=['GET'])
@login_required
def confirm_email(token):
    # Attempt to get the data from the token
    data = check_token(email_signer, token)
    if data is not None:
        # Change the users e-mail
        uid = data['uid']
        email = data['email']
        if uid:
            be_change_email(uid, email)
            flash('Your e-mail has now been changed', 'success')
            return redirect(url_for('signin'))

    # The token is either out of date or has been tampered with
    flash('Invalid token. Stop mucking around', 'error')
    return redirect(url_for('change_email'))


@app.route('/settings/password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = PasswordChangeForm(request.form)
    if request.method == 'POST':
        if form.validate():
            if authenticate(current_user['username'], form.password.data):
                # Update the users password!
                be_change_password(current_user['uid'], form.new_password.data)
                flash('Your password has successfully been update!', 'success')
        else:
            flash('Oh no! There are errors in your change password form.',
                  'error')
    return render_template('change_password.html', form=form)


@app.route('/settings/delete', methods=['GET', 'POST'])
@login_required
def delete_account():
    form = DeleteAccountForm(request.form)
    if request.method == 'POST':
        if authenticate(current_user['username'], form.password.data):
            uid = int(current_user['uid'])
            logout()
            # This is still rather buggy!
            be_delete_account(uid)
            flash('Your account has been deleted!<br/>'
                  'We hope you have enjoyed Pjuu', 'information')
        else:
            flash('Invalid password', 'error')
    return render_template('delete_account.html', form=form)
