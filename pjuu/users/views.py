# -*- coding: utf8 -*-
# Stdlib imports
from hashlib import md5
import math
from time import gmtime, strftime
# 3rd party imports
from flask import (abort, flash, redirect, render_template, request,
                   url_for)
# Pjuu imports
from pjuu import app
from pjuu.auth.backend import current_user, get_uid, is_safe_url
from pjuu.auth.decorators import login_required
from pjuu.posts.backend import check_post, get_post
from pjuu.posts.forms import PostForm
from .backend import (follow_user, unfollow_user, get_profile, get_feed,
                      get_posts, get_followers, get_following, is_following,
                      get_comments)


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
    millnames = ['', 'K', 'M', 'B', 'T', 'Q', 'Qt']
    millidx = max(0, min(len(millnames) - 1,
                         int(math.floor(math.log10(abs(number)) / 3.0))))
    result = '%.0f%s' % (number / 10 ** (3 * millidx), millnames[millidx])
    if n < 0:
        return '-' + result
    return result


@app.template_filter('timeify')
def timeify(time):
    """
    Takes integer epoch time and returns a DateTime string for display.
    If this conversion fails this function will return Unknown
    """
    try:
        time = int(time)
        return strftime("%a %d %b %Y %H:%M:%S", gmtime(time))
    except:
        # Dirty... catching ALL exceptions
        return "Unknown"


@app.route('/', methods=['GET'])
# Do not place login_required on this method handled by view for prettiness
def feed():
    if not current_user:
        return redirect(url_for('signin'))
    # Pagination
    page = request.values.get('page', None)
    try:
        page = int(page)
    except:
        page = 1
    # Get feed pagination
    pagination = get_feed(int(current_user['uid']), page)
    # Post form
    post_form = PostForm()
    return render_template('users/feed.html', pagination=pagination,
                           post_form=post_form)


@app.route('/<username>', methods=['GET'])
@login_required
def profile(username):
    """
    This is reffered to as Posts on the site. It will show the
    users posts.
    """
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
    # Get the posts pagination
    pagination = get_posts(uid, page)
    # Post form
    post_form = PostForm()
    return render_template('users/posts.html', profile=profile,
                           pagination=pagination, post_form=post_form)


@app.route('/<username>/<int:pid>', methods=['GET'])
@login_required
def view_post(username, pid):
    if not check_post(username, pid):
        return abort(404)

    # Pagination
    page = request.values.get('page', None)
    try:
        page = int(page)
    except:
        page = 1

    # Get post
    post = get_post(pid)
    # Get comments
    pagination = get_comments(pid, page)
    post_form = PostForm()
    return render_template('users/view_post.html', post=post,
                           pagination=pagination, post_form=post_form)


@app.route('/<username>/following', methods=['GET'])
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
                           pagination=following, post_form=post_form)


@app.route('/<username>/followers', methods=['GET'])
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
    followers = get_followers(uid, page)
    # Post form
    post_form = PostForm()
    return render_template('users/followers.html', profile=profile,
                           pagination=followers, post_form=post_form)


@app.route('/<username>/follow', methods=['GET'])
@login_required
def follow(username):
    uid = get_uid(username)

    if uid is None:
        abort(404)

    # We redirect so we don't have to user AJAX straigh away
    redirect_url = request.values.get('next', None)
    if not redirect_url or not is_safe_url(redirect_url):
        redirect_url = url_for('profile', username=username)

    # Follow user
    if follow_user(current_user['uid'], uid):
        flash('You have started following %s' % username, 'information')
    return redirect(redirect_url)


@app.route('/<username>/unfollow', methods=['GET'])
@login_required
def unfollow(username):
    uid = get_uid(username)

    if uid is None:
        abort(404)

    # We redirect so we don't have to user AJAX straigh away
    redirect_url = request.values.get('next', None)
    if not redirect_url or not is_safe_url(redirect_url):
        redirect_url = url_for('profile', username=username)

    # Unfollow user
    if unfollow_user(current_user, user):
        flash('You are no longer following %s' % username, 'information')
    return redirect(redirect_url)


@app.route('/notifications', methods=['GET'])
@login_required
def notifications():
    return render_template('users/notifications.html')


@app.route('/search', methods=['GET'])
@login_required
def search():
    """
    Handles searching of users. This is all done via a GET query.
    """
    query = request.args['query'] or None
    users = {}
    return render_template('users/search.html', query=query,
                           users=users)


@app.route('/settings/profile', methods=['GET', 'POST'])
@login_required
def settings_profile():
    return render_template('users/settings_profile.html')


@app.route('/settings/account', methods=['GET'])
@login_required
def settings_account():
    return render_template('users/settings_account.html')