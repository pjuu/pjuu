# 3rd party imports
from flask import (abort, flash, g, redirect, render_template, request,
                   session, url_for)
from werkzeug import check_password_hash, generate_password_hash
# Pjuu imports
from pjuu import app, r
from pjuu.auth.backend import current_user, get_uid, is_safe_url
from pjuu.auth.decorators import login_required
from pjuu.posts.forms import PostForm
from .backend import follow_user, unfollow_user, get_profile


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

    return render_template('users/feed.html', post_form=post_form)


@app.route('/<username>')
@login_required
def profile(username):    
    uid = get_uid(username)
    if uid is None:
        abort(404)

    profile = get_profile(uid)

    post_form = PostForm()
    return render_template('users/posts.html', profile=profile,
                           post_form=post_form)


@app.route('/<username>/following')
@login_required
def following(username):
    user = User.query.filter_by(username=username).first()

    if user is None:
        abort(404)

    page = request.values.get('page', None)
    try:
        page = int(page)
    except:
        page = 1

    post_form = PostForm()
    following = user.following\
                .paginate(page, app.config['PROFILE_ITEMS_PER_PAGE'], False)
    return render_template('users/following.html', user=user,
                           post_form=post_form, user_list=following)


@app.route('/<username>/followers')
@login_required
def followers(username):
    user = User.query.filter_by(username=username).first()

    if user is None:
        abort(404)

    page = request.values.get('page', None)
    try:
        page = int(page)
    except:
        page = 1

    post_form = PostForm()
    followers = user.followers\
                .paginate(page, app.config['PROFILE_ITEMS_PER_PAGE'], False)
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
        flash('You have started following this user', 'information')
    return redirect(redirect_url)


@app.route('/<username>/unfollow')
@login_required
def unfollow(username):
    user = User.query.filter_by(username=username).first()

    if user is None:
        abort(404)

    redirect_url = request.values.get('next', None)
    if not redirect_url or not is_safe_url(redirect_url):
        redirect_url=url_for('profile', username=username)

    if unfollow_user(current_user, user):
        flash('You have unfollowed this user', 'success')
    return redirect(redirect_url)


@app.route('/search', methods=['GET'])
@login_required
def search():
    """
    Handles searching of users. This is all done via a query to GET.
    """
    page = request.values.get('page', None)
    try:
        page = int(page)
    except:
        page = 1


    query = request.values.get('query', None)
    
    if query is not None and query != '':
        query = '%' + query + '%'
        results = User.query.filter(User.username.ilike(query))\
                  .paginate(page, app.config['PROFILE_ITEMS_PER_PAGE'], False)
    else:
        return redirect(url_for('feed'))
    return render_template('users/search.html', query=query,
                           user_list=results)


@app.route('/notifications')
@login_required
def notifications():
    notifications = []
    return render_template('users/notifications.html',
                           notifications=notifications)


@app.route('/settings/profile', methods=['GET', 'POST'])
@login_required
def settings_profile():
    pass
