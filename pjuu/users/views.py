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
    # login_required is not needed for this function to keep the base
    # url pretty :)
    post_form = PostForm()
    if not current_user:
        return redirect(url_for('signin'))
    return render_template('users/feed.html', post_form=post_form)


@app.route('/<username>')
@login_required
def profile(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        abort(404)
    post_form = PostForm()
    posts = Post.query.filter_by(author=user.id).order_by(Post.created.desc())
    return render_template('users/posts.html', user=user, posts_list=posts,
                           post_form=post_form)


@app.route('/<username>/following')
@login_required
def following(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        abort(404)
    post_form = PostForm()
    following = user.following.all()
    return render_template('users/following.html', user=user,
                           post_form=post_form, user_list=following)


@app.route('/<username>/followers')
@login_required
def followers(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        abort(404)
    post_form = PostForm()
    followers = user.followers.all()
    return render_template('users/followers.html', user=user,
                           post_form=post_form, user_list=followers)


@app.route('/<username>/follow')
@login_required
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        abort(404)
    if not user == current_user:
        current_user.following.append(user)
        try:
            db.session.add(current_user)
            db.session.commit()
        except:
            db.session.rollback()
    return redirect(url_for('profile', username=username))


@app.route('/<username>/unfollow')
@login_required
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        abort(404)
    if not user == current_user:
        current_user.following.remove(user)
        try:
            db.session.add(current_user)
            db.session.commit()
        except:
            db.session.rollback()
    return redirect(url_for('profile', username=username))


@app.route('/<username>/<int:post_id>')
@login_required
def view_post(username, post_id):
    post = Post.query.get(post_id)
    user = User.query.filter_by(username=username).first()
    if not user or not post or not post.user.username.lower() == user.username.lower():
        abort(404)
    return render_template('users/post.html', user=user, post=post)
