# Stdlib imports
from hashlib import md5
import math
# 3rd party imports
from flask import (abort, flash, g, redirect, render_template, request,
                   session, url_for)
from werkzeug import check_password_hash, generate_password_hash
# Pjuu imports
from pjuu import app
from pjuu.auth.backend import current_user, get_uid, is_safe_url
from pjuu.auth.decorators import login_required
from pjuu.posts.forms import PostForm
from .backend import (follow_user, unfollow_user, get_profile, get_feed,
                      get_posts, get_followers, get_following, is_following)


@app.template_filter('following')
def following_filter(uid):
    '''
    Checks if current user is following the user with id piped to filter 
    '''
    return is_following(current_user['uid'], uid)


@app.template_filter('gravatar')
def gravatar(email, size=24):
    """
    Returns gravatar URL for a given email with the size size.
    """
    return 'https://www.gravatar.com/avatar/%s?d=identicon&s=%d' % \
        (md5(email.strip().lower().encode('utf-8')).hexdigest(), size)


@app.template_filter('millify')
def millify(n):
    """
    Template filter to millify numbers, e.g. 1K, 2M, 1.25B
    """
    n = int(n)
    if n == 0:
        return n
    number = n
    if n < 0:
        number = abs(n)
    millnames = ['','K','M','B','T','Q','Qt']
    millidx = max(0, min(len(millnames) - 1,
                  int(math.floor(math.log10(abs(number)) / 3.0))))
    result = '%.0f%s' % (number / 10 ** (3 * millidx), millnames[millidx])
    if n < 0:
        return '-' + result
    return result


@app.route('/')
def feed():
    # login_required is not needed for this function to keep the base
    # url pretty :)
    if not current_user:
        return redirect(url_for('signin'))
    # Pagination
    page = request.values.get('page', None)
    try:
        page = int(page)
    except:
        page = 1
    pagination = get_feed(int(current_user['uid']), page)

    # Post form
    post_form = PostForm()
    return render_template('users/feed.html', post_form=post_form,
                           pagination=pagination)


@app.route('/<username>')
@login_required
def profile(username):    
    uid = get_uid(username)
    
    if uid is None:
        abort(404)

    # Data
    profile = get_profile(uid)

    # Pagination
    page = request.values.get('page', None)
    try:
        page = int(page)
    except:
        page = 1

    # Get the posts
    pagination = get_posts(uid, page)
    # Post form
    post_form = PostForm()
    return render_template('users/posts.html', profile=profile,
                           pagination=pagination, post_form=post_form)


@app.route('/<username>/following')
@login_required
def following(username):
    uid = get_uid(username)
    
    if uid is None:
        abort(404)

    # Data
    profile = get_profile(uid)
    
    # Pagination
    page = request.values.get('page', None)
    try:
        page = int(page)
    except:
        page = 1

    # Get a list of users you are following
    following = get_following(uid, page)
    # Post form
    post_form = PostForm()
    return render_template('users/following.html', profile=profile,
                           items=following, post_form=post_form)


@app.route('/<username>/followers')
@login_required
def followers(username):
    uid = get_uid(username)
    
    if uid is None:
        abort(404)
        
    # Data
    profile = get_profile(uid)
    
    # Pagination
    page = request.values.get('page', None)
    try:
        page = int(page)
    except:
        page = 1

    # Get a list of users you are following
    following = get_followers(uid, page)
    # Post form
    post_form = PostForm()
    return render_template('users/followers.html', profile=profile,
                           items=following, post_form=post_form)


@app.route('/<username>/follow')
@login_required
def follow(username):
    uid = get_uid(username)
    
    if uid is None:
        abort(404)

    # We redirect so we don't have to user AJAX straigh away
    redirect_url = request.values.get('next', None)
    if not redirect_url or not is_safe_url(redirect_url):
        redirect_url=url_for('profile', username=username)

    # Follow user
    if follow_user(current_user['uid'], uid):
        flash('You have started following this user', 'information')
    return redirect(redirect_url)


@app.route('/<username>/unfollow')
@login_required
def unfollow(username):
    uid = get_uid(username)

    if uid is None:
        abort(404)

    # We redirect so we don't have to user AJAX straigh away
    redirect_url = request.values.get('next', None)
    if not redirect_url or not is_safe_url(redirect_url):
        redirect_url=url_for('profile', username=username)

    # Unfollow user
    if unfollow_user(current_user, user):
        flash('You have unfollowed this user', 'success')
    return redirect(redirect_url)


@app.route('/search', methods=['GET'])
@login_required
def search():
    """
    Handles searching of users. This is all done via a query to GET.
    """
    users = {}
    return render_template('users/search.html', query=query,
                           users=users)


@app.route('/settings/profile', methods=['GET', 'POST'])
@login_required
def settings_profile():
    pass


@app.route('/settings/account', methods=['GET'])
@login_required
def settings_account():
    pass