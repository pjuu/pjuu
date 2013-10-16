# 3rd party imports
from flask import (abort, flash, g, redirect, render_template, request,
                   session, url_for)
from werkzeug import check_password_hash, generate_password_hash

# Pjuu imports
from pjuu import app, db
from pjuu.auth.backend import current_user
from pjuu.auth.decorators import login_required
from pjuu.users.models import User
from pjuu.posts.forms import PostForm
from pjuu.posts.models import Post


@app.route('/')
def feed():
    post_form = PostForm()
    if not current_user:
        return redirect(url_for('login'))
    return render_template('users/feed.html', post_form=post_form,
                           author_title="Create a new post")


@app.route('/<username>')
@login_required
def profile(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        abort(404)
    post_form = PostForm()
    posts = Post.query.filter_by(author=user.id).order_by(Post.created.desc())
    return render_template('users/posts.html', user=user, posts=posts,
                           author_title="Create a new post", post_form=post_form)


@app.route('/<username>/following')
def following(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        abort(404)
    following = user.following.all()
    return render_template('users/following.html', user=user, following=following)


@app.route('/<username>/followers')
def followers(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        abort(404)
    followers = user.followers.all()
    return render_template('users/followers.html', user=user, followers=followers)


@app.route('/<username>/follow')
def follow(username):
    return "Follow"


@app.route('/<username>/unfollow')
def unfollow(username):
    return "Unfollow"
