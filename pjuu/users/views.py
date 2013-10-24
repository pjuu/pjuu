# 3rd party imports
from flask import (abort, flash, g, redirect, render_template, request,
                   session, url_for)
from werkzeug import check_password_hash, generate_password_hash

# Pjuu imports
from pjuu import app, db
from pjuu.auth.backend import current_user, is_safe_url
from pjuu.auth.decorators import login_required
from pjuu.users.models import User
from pjuu.posts.forms import PostForm
from pjuu.posts.models import Post
from .backend import follow_user, unfollow_user


@app.template_filter('following')
def following_filter(user):
    '''
    Checks if current user is following the user with id piped to filter 
    '''
    return user in current_user.following.all()


@app.route('/')
def feed():
    # login_required is not needed for this function to keep the base
    # url pretty :)
    post_form = PostForm()
    if not current_user:
        return redirect(url_for('signin'))
    #TODO: Sort of the feed system. THIS IS VERY IMPORTANT
    # This is temporary and will not scale.

    page = request.values.get('page', None)
    try:
        page = int(page)
    except:
        page = 1

    following = current_user.following.all()
    following.append(current_user)
    posts = Post.query.filter(Post.author.in_(u.id for u in following)).order_by(Post.created.desc()).paginate(page, 20, False)
    return render_template('users/feed.html', post_form=post_form, posts_list=posts)


@app.route('/<username>')
@login_required
def profile(username):    
    user = User.query.filter_by(username=username).first()
    if user is None:
        abort(404)

    page = request.values.get('page', None)
    try:
        page = int(page)
    except:
        page = 1

    post_form = PostForm()
    posts = Post.query.filter_by(author=user.id).order_by(Post.created.desc()).paginate(page, 10, False)
    return render_template('users/posts.html', user=user, posts_list=posts,
                           post_form=post_form)


@app.route('/<username>/avatar')
def avatar(username):
    """
    Future usage to remove the MD5'd e-mail from the Gravatar URL.
    """
    pass


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

    redirect_url = request.values.get('next', None)
    if not redirect_url or not is_safe_url(redirect_url):
        redirect_url=url_for('profile', username=username)

    if follow_user(current_user, user):
        flash('You have started following this user')
    return redirect(redirect_url)


@app.route('/<username>/unfollow')
@login_required
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        abort(404)

    redirect_url = request.values.get('next', None)
    if not redirect_url or not is_safe_url(redirect_url):
        redirect_url=url_for('profile', username=usernmae)

    if unfollow_user(current_user, user):
        flash('You have unfollowed this user', 'success')
    return redirect(redirect_url)


@app.route('/<username>/<int:post_id>')
@login_required
def view_post(username, post_id):
    post = Post.query.get(post_id)
    user = User.query.filter_by(username=username).first()
    # How can this line fit under 80 char correctly?
    if not user or not post or not post.user.username.lower() == user.username.lower():
        abort(404)
    return render_template('users/post.html', user=user, post=post)


@app.route('/settings')
@login_required
def settings():
    return render_template('users/settings.html')


@app.route('/search')
@login_required
def search():
    """
    Handles searching of users. This is all done via a query to GET.
    """
    results = []
    return render_template('users/search.html', results=results)


@app.route('/notifications')
@login_required
def notifications():
    notifications = []
    return render_template('users/notifications.html',
                           notifications=notifications)
