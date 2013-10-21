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
                      logout, create_account)
from .decorators import anonymous_required, login_required
from .forms import ForgotForm, LoginForm, ResetForm, SignupForm


@app.context_processor
def inject_user():
    """
    Injects `current_user` into the Jinja environment
    """
    return dict(current_user=current_user)


@app.route('/signin', methods=['GET', 'POST'])
@anonymous_required
def signin():
    form = LoginForm(request.form)
    if request.method == 'POST':
        # Handles the passing of the next argument to the login view
        redirect_url = request.values.get('next', None)
        if not redirect_url or not is_safe_url(redirect_url):
            redirect_url=url_for('feed')
        if form.validate():
            username = form.username.data
            password = form.password.data
            # Calls authenticate from backend.py
            user = authenticate(username, password)
            if user is not None:
                if not user.active:
                    flash('Please activate your account. Check your e-mail',
                          'warning')
                elif user.banned:
                    flash('Your account has been banned. Naughty boy',
                          'warning')
                else:
                    login(user)
                    return redirect(redirect_url)
            else:
                flash('Invalid user name or password', 'error')
        else:
            flash('Invalid user name or password', 'error')
    return render_template('auth/signin.html', form=form)


@app.route('/signout')
def signout():
    if current_user:
        logout()
        flash('Successfully logged out!', 'success')
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
                # TODO Generate activation token
                # Sends activation e-mail to new user
                send_mail('Welcome', [new_user.email],
                          text_body=render_template('auth/welcome.email.txt'),
                          html_body=render_template('auth/welcome.email.html'))
                flash('Yay! You\'ve signed up. Please log in.', 'success')
                return redirect(url_for('signin'))
        # This will fire if the form is invalid
        flash('Oh no! There are errors in your signup form', 'error')
    return render_template('auth/signup.html', form=form)


@app.route('/signup/<token>', methods=['GET', 'POST'])
@anonymous_required
def activate(token):
    pass


@app.route('/forgot', methods=['GET', 'POST'])
@anonymous_required
def forgot():
    form = ForgotForm(request.form)
    return render_template('auth/forgot.html', form=form)


@app.route('/forgot/<token>', methods=['GET', 'POST'])
@anonymous_required
def password_reset(token):
    form = ResetForm(request.form)
    return render_template('auth/reset.html', form=form)
