# 3rd party imports
from flask import (abort, flash, g, redirect, render_template, request,
                   session, url_for)
from werkzeug import check_password_hash, generate_password_hash

# Pjuu imports
from pjuu import app, db
from pjuu.auth.backend import current_user
from pjuu.auth.decorators import login_required


@app.route('/')
def feed():
    if not current_user:
        return redirect(url_for('login'))
    return render_template('users/feed.html')


@app.route('/<username>')
@login_required
def profile(username):
    return "Profile"


@app.route('/<username>/following')
def following(username):
    return "Following"


@app.route('/<username>/followers')
def followers(username):
    return "Followers"


@app.route('/<username>/follow')
def follow(username):
    return "Follow"


@app.route('/<username>/unfollow')
def unfollow(username):
    return "Unfollow"
