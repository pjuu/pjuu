# -*- coding: utf8 -*-

"""
Description:
    The actual endpoints for Pjuu users package

Licence:
    Copyright 2014 Joe Doherty <joe@pjuu.com>

    Pjuu is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    Pjuu is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

# Stdlib imports
from hashlib import md5
import math
# 3rd party imports
from flask import (current_app as app, abort, flash, redirect, render_template,
                   request, url_for, jsonify)
# Pjuu imports
from pjuu.auth import current_user
from pjuu.auth.backend import get_uid, get_uid_username
from pjuu.auth.decorators import login_required
from pjuu.lib import handle_next, timestamp
from pjuu.lib.pagination import handle_page
from pjuu.posts.backend import check_post, get_post, parse_tags
from pjuu.posts.forms import PostForm
from pjuu.users.forms import ChangeProfileForm, SearchForm
from pjuu.users.backend import (follow_user, unfollow_user, get_profile,
                                get_feed, get_posts, get_followers,
                                get_following, is_following, set_about,
                                get_alerts, get_comments, search as be_search,
                                i_has_alerts as be_i_has_alerts,
                                delete_alert as be_delete_alert)


@app.template_filter('following')
def following_filter(profile):
    """
    Checks if current user is following the user with id piped to filter
    """
    return is_following(current_user.get('uid'), profile.get('uid'))


@app.template_filter('avatar')
def avatar_filter(email, size=24):
    """
    Returns gravatar URL for a given email with the size size.

    Note: In future this will return a Pjuu avatar URL
    """
    return 'https://www.gravatar.com/avatar/%s?d=identicon&s=%d' % \
           (md5(email.strip().lower().encode('utf-8')).hexdigest(), size)


@app.template_filter('nameify')
def nameify_filter(body):
    """
    Will highlight user names inside a post. This is done after urlize.

    These uses the same parse_tags() function as to identify tags for
    alerts

    TODO This may be overkill.
    This requires manual escaping of the post|comment|about messages. In
    Jinja2 you have to do to the following to get the posts to show as we
    want:

    {% autoescape false %}
    post.body|e|urlize|nameify
    {% endautoescape %}

    The 'e' filter is needed as we have had to turn auto escape off.
    """
    tags = parse_tags(body, deduplicate=True)
    offset = 0
    for tag in tags:
        # Calculate the left and right hand sides of the tag
        # These add offset as we go, we are changing the length of the string
        # each time!
        left = tag[3][0] + offset
        right = tag[3][1] + offset
        # Build the link
        link = "<a href=\"/%s\">%s</a>" % (tag[1], tag[2])
        # Calculate the offset to adjust rest of tag boundries
        offset += len(link) - len(tag[2])
        # Add the link in place of the '@' tag
        body = (body[:left] + link + body[right:])
    return body


@app.template_filter('millify')
def millify_filter(n):
    """
    Template filter to millify numbers, e.g. 1K, 2M, 1.25B
    """
    try:
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
    except (TypeError, ValueError):
        return "Err"


@app.template_filter('timeify')
def timeify_filter(time):
    """
    Takes integer epoch time and returns a DateTime string for display.
    If this conversion fails this function will return "Err"
    """
    try:
        # Please not that time is now a floating point value for extra
        # precision. We don't really need this when displaying it to the users
        # however.
        # Time can't be coverted directly to a int as it is a float point repr
        time = int(timestamp() - float(time))

        multiples = [
            (31536000, 'year'),
            (2592000, 'month'),
            (604800, 'week'),
            (86400, 'day'),
            (3600, 'hour'),
            (60, 'minute'),
            (1, 'second')
        ]

        # Find the closest time multiple since this post was posted
        # Work out the number of these multiples and return the string
        for multiple in multiples:
            if time < multiple[0]:
                continue
            number_of = math.floor(time / multiple[0])
            if number_of > 1:
                time_frame = multiple[1] + 's'
            else:
                time_frame = multiple[1]

            return "{0} {1} ago".format(int(number_of), time_frame)

        # Default return means that this was checked less than a second ago
        return "Less than a second ago"

    except (TypeError, ValueError):
        return "Err"


@app.template_filter('has_alerts')
def has_alerts_filter(uid):
    """
    Check to see if the user has any alerts. Should only ever really be Used
    with current_user

    Uses the i_has_alerts() backend function
    """
    return be_i_has_alerts(uid)


@app.route('/', methods=['GET'])
# Do not place login_required on this method handled by view for prettiness
def feed():
    """
    Returns the users feed
    """
    if not current_user:
        return redirect(url_for('signin'))

    # Pagination
    page = handle_page(request)
    # Get feed pagination
    pagination = get_feed(current_user.get('uid'), page)

    # Post form
    post_form = PostForm()
    return render_template('feed.html', pagination=pagination,
                           post_form=post_form)


@app.route('/<username>', methods=['GET'])
@login_required
def profile(username):
    """
    This is refered to as Posts on the site. It will show the
    users posts.
    """
    uid = get_uid_username(username)

    if uid is None:
        abort(404)

    # Data
    profile = get_profile(uid)

    # Pagination
    page = handle_page(request)
    # Get the posts pagination
    pagination = get_posts(uid, page)

    # Post form
    post_form = PostForm()
    return render_template('posts.html', profile=profile,
                           pagination=pagination, post_form=post_form)


@app.route('/<username>/<pid>', methods=['GET'])
@login_required
def view_post(username, pid):
    """
    Displays a post along with its comments paginated. I am not sure if this
    should be here or in the 'posts' app.
    """
    if not check_post(get_uid(username), pid):
        return abort(404)

    # Pagination
    page = handle_page(request)

    # Get post
    post = get_post(pid)
    # Get comments
    pagination = get_comments(pid, page)
    post_form = PostForm()
    return render_template('view_post.html', post=post,
                           pagination=pagination, post_form=post_form)


@app.route('/<username>/following', methods=['GET'])
@login_required
def following(username):
    """
    Returns all users following the current user as a pagination
    """
    uid = get_uid(username)

    if uid is None:
        abort(404)

    # Data
    profile = get_profile(uid)

    # Pagination
    page = handle_page(request)

    # Get a list of users you are following
    following = get_following(uid, page)
    # Post form
    post_form = PostForm()
    return render_template('following.html', profile=profile,
                           pagination=following, post_form=post_form)


@app.route('/<username>/followers', methods=['GET'])
@login_required
def followers(username):
    """
    Returns all a users followers as a pagination object
    """
    uid = get_uid(username)

    if uid is None:
        abort(404)

    # Data
    _profile = get_profile(uid)

    # Pagination
    page = handle_page(request)

    # Get a list of users you are following
    _followers = get_followers(uid, page)
    # Post form
    post_form = PostForm()
    return render_template('followers.html', profile=_profile,
                           pagination=_followers, post_form=post_form)


@app.route('/<username>/follow', methods=['GET'])
@login_required
def follow(username):
    """
    Used to follow a user
    """
    redirect_url = handle_next(request, url_for('following',
                               username=current_user.get('username')))

    uid = get_uid(username)

    # If we don't get a uid from the username the page doesn't exist
    if uid is None:
        abort(404)

    # Unfollow user, ensure the user doesn't unfollow themself
    if uid != current_user.get('uid'):
        if follow_user(current_user.get('uid'), uid):
            flash('You have started following %s' % username, 'success')
    else:
        flash('You can\'t follow/unfollow yourself', 'information')

    return redirect(redirect_url)


@app.route('/<username>/unfollow', methods=['GET'])
@login_required
def unfollow(username):
    """
    Used to unfollow a user
    """
    redirect_url = handle_next(request, url_for('following',
                               username=current_user.get('username')))

    uid = get_uid(username)

    # If we don't get a uid from the username the page doesn't exist
    if uid is None:
        abort(404)

    # Unfollow user, ensure the user doesn't unfollow themself
    if uid != current_user.get('uid'):
        if unfollow_user(current_user.get('uid'), uid):
            flash('You are no longer following %s' % username, 'success')
    else:
        flash('You can\'t follow/unfollow yourself', 'information')

    return redirect(redirect_url)


@app.route('/search', methods=['GET'])
@login_required
def search():
    """
    Handles searching of users. This is all done via a GET query.
    There should be _NO_ CSRF as this will appear in the URL and look shit
    """
    form = SearchForm(request.form)

    # Get the query string. If its not there return an empty string
    query = request.args.get('query', '')

    _results = be_search(query)
    return render_template('search.html', form=form, query=query,
                           pagination=_results)


@app.route('/settings', methods=['GET', 'POST'])
@app.route('/settings/profile', methods=['GET', 'POST'])
@login_required
def settings_profile():
    """
    Allows users to customize their profile direct from this view.
    """
    form = ChangeProfileForm(request.form)
    if request.method == 'POST':
        if form.validate():
            # Update current_user, this was highlighted by Ant is issue 1
            current_user['about'] = form.about.data
            # Set the users new about in Redis
            set_about(current_user.get('uid'), form.about.data)
            flash('Your profile has been updated', 'success')
        else:
            flash('Oh no! There are errors in your form', 'error')

    return render_template('settings_profile.html', form=form)


@app.route('/alerts', methods=['GET'])
@login_required
def alerts():
    """
    Display a users alerts (notifications) to them on the site.
    """
    uid = current_user.get('uid')

    # Pagination
    page = handle_page(request)

    _results = get_alerts(uid, page)
    return render_template('alerts.html', pagination=_results)


@app.route('/alerts/<aid>/delete', methods=['GET'])
@login_required
def delete_alert(aid):
    """
    Remove an alert id (aid) from a users alerts feed
    """
    uid = current_user.get('uid')
    # Handle next
    redirect_url = handle_next(request, url_for('alerts'))

    if be_delete_alert(uid, aid):
        flash('Alert has been hidden', 'success')

    return redirect(redirect_url)


@app.route('/i-has-alerts', methods=['GET'])
def i_has_alerts():
    """
    Will return a simple JSON response to denote if the current user has any
    alerts since last time this was called.

    This will be passed in with the template but will allow something like
    jQuery to check.
    """
    # We don't want this view to redirect to signin so we will throw a 403
    # this will make jQuery easier to use with this endpoint
    if not current_user:
        return abort(403)

    uid = current_user.get('uid')

    return jsonify(result=be_i_has_alerts(uid))
