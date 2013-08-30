# 3rd party imports
from flask import (abort, flash, g, redirect, render_template, request,
                   session, url_for)
from werkzeug import check_password_hash, generate_password_hash

# Pjuu imports
from pjuu import app, db
from pjuu.lib.mail import send_mail
from pjuu.users.models import User

# Package imports
from .backend import (authenticate, current_user, is_safe_url,
                      login as plogin, logout as plogout)
from .decorators import anonymous_required, login_required
from .forms import ForgotForm, LoginForm, SignupForm


@app.context_processor
def inject_user():
    '''
    Injects current `current_user` into the template environment as `user`
    '''
    return dict(user=current_user)


@app.route('/signin', methods=['GET', 'POST'])
@anonymous_required
def login():
    form = LoginForm(request.form)
    if request.method == 'POST':
        # Handles the passing of the next argument to the login view
        redirect_url = request.values.get('next', None)
        if not redirect_url or not is_safe_url(redirect_url):
            redirect_url=url_for('feed')
        if form.validate():
            username = form.username.data
            password = form.password.data
            user = authenticate(username, password)
            if user is not None:
                plogin(user)
                return redirect(redirect_url)
            flash('Invalid user name or password', 'error')
    return render_template('auth/login.html', form=form)


@app.route('/logout')
def logout():
    if current_user:
        plogout()
        flash('Successfully logged out!', 'success')
    return redirect(url_for('login'))


@app.route('/signup', methods=['GET', 'POST'])
@anonymous_required
def signup():
    form = SignupForm(request.form)
    if request.method == 'POST':
        if form.validate():
            # User successfully signed up, create an account
            new_user = User(form.username.data, form.email.data,
                            form.password.data)
            db.session.add(new_user)
            db.session.commit()
            send_mail('Welcome to Pjuu', [new_user.email], 'Welcome')
            flash('Yay! Welcome. You can now login.', 'success')
            return redirect(url_for('login'))
        flash('Oh no! There are errors in your signup form', 'error')
    return render_template('auth/signup.html', form=form)

@app.route('/forgot', methods=['GET', 'POST'])
@anonymous_required
def forgot():
    form = ForgotForm(request.form)
    return render_template('auth/forgot.html', form=form)
