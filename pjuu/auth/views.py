# 3rd party imports
from flask import (abort, flash, g, redirect, render_template, request,
                   session, url_for)
from werkzeug import check_password_hash, generate_password_hash

# Pjuu imports
from pjuu import app, db
from pjuu.lib.mail import send_mail
from pjuu.users.models import User

# Package imports
from .backend import (authenticate, current_user, is_safe_url, login,
                      logout, create_account, activate_signer, forgot_signer,
                      email_signer, generate_token, check_token,
                      activate as be_activate,
                      change_password as be_change_password,
                      get_username, check_username)
from .decorators import anonymous_required, login_required
from .forms import (ForgotForm, LoginForm, ResetForm, SignupForm,
                    PasswordChangeForm, EmailChangeForm, DeleteAccountForm)


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
        redirect_url = request.values.get('next', None)
        if not redirect_url or not is_safe_url(redirect_url):
            redirect_url = url_for('feed')

        if form.validate():
            # Calls authenticate from backend.py
            user = authenticate(form.username.data, form.password.data)
            if user is not None:
                if not user.active:
                    flash('Please activate your account. Check your e-mails.',
                          'warning')
                elif user.banned:
                    flash('You have been banned. Naughty boy.',
                          'warning')
                else:
                    login(user)
                    return redirect(redirect_url)
            else:
                flash('Invalid user name or password.', 'error')
        else:
            flash('Invalid user name or password.', 'error')

    return render_template('auth/signin.html', form=form)


@app.route('/signout', methods=['GET'])
def signout():
    """
    Logs a user out.
    This will always go to /signin regardless. If user was actually
    logged out it will let them know.
    """
    if current_user:
        logout()
        flash('Successfully logged out.', 'success')
    return redirect(url_for('signin'))


@app.route('/signup', methods=['GET', 'POST'])
@anonymous_required
def signup():
    form = SignupForm(request.form)
    if request.method == 'POST':
        if form.validate():
            # User successfully signed up, create an account
            new_user = create_account(form.username.data, form.email.data,
                                      form.password.data)
            if new_user:
                token = generate_token(activate_signer,
                                       {'username': new_user.username})
                send_mail('Activation', [new_user.email],
                          text_body=render_template('emails/activate.txt',
                                                    token=token),
                          html_body=render_template('emails/activate.html',
                                                    token=token))
                flash('Yay! You\'ve signed up.<br>Please check your e-mails '
                      'to activate your account.', 'success')
                return redirect(url_for('signin'))
        # This will fire if the form is invalid
        flash('Oh no! There are errors in your signup form.', 'error')
    return render_template('auth/signup.html', form=form)


@app.route('/signup/<token>', methods=['GET'])
@anonymous_required
def activate(token):
    # Attempt to get the data from the token
    data = check_token(activate_signer, token)

    if data is not None:
        # Attempt to activate the users account
        user = get_username(data['username'])
        if user:
            be_activate(user)
            # If we have got to this point. Send a welcome e-mail :)
            send_mail('Welcome', [user.email],
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
        user = get_username(form.username.data)
        if user:
            # Only send e-mails to user which exist.
            token = generate_token(forgot_signer,
                                   {'username': user.username})
            send_mail('Password reset', [user.email],
                      text_body=render_template('emails/forgot.txt',
                                                token=token),
                      html_body=render_template('emails/forgot.html',
                                                token=token))
        flash('If we have you user record we have e-mailed a reset '
              'link too you.', 'information')
        return redirect(url_for('signin'))
    return render_template('auth/forgot.html', form=form)


@app.route('/forgot/<token>', methods=['GET', 'POST'])
@anonymous_required
def reset(token):
    form = ResetForm(request.form)
    data = check_token(forgot_signer, token)

    if data is not None:
        if request.method == 'POST':
            if form.validate():
                user = get_username(data['username'])
                be_change_password(user, form.password.data)
                flash('Your password has been reset. Please login.', 'success')
                return redirect(url_for('signin'))
            else:
                flash('Oh no! There are errors in your reset form.', 'error')
    else:
        flash('Invalid token.', 'error')
        return redirect(url_for('signin'))

    return render_template('auth/reset.html', form=form)
