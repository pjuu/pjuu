# -*- coding: utf8 -*-

"""Flask endpoints.

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2015 Joe Doherty

"""

# Stdlib imports
from datetime import datetime
import math
# 3rd party imports
from flask import (abort, flash, redirect, render_template, request, url_for,
                   Blueprint, current_app as app, send_file)
# Pjuu imports
from pjuu.auth import current_user
from pjuu.auth.utils import get_uid, get_uid_username, get_user
from pjuu.auth.decorators import login_required
from pjuu.lib import handle_next, timestamp
from pjuu.lib.pagination import handle_page
from pjuu.lib.uploads import get_upload
from pjuu.posts.backend import get_posts
from pjuu.posts.forms import PostForm
from pjuu.users.forms import ChangeProfileForm, SearchForm
from pjuu.users.backend import (
    follow_user, unfollow_user, get_profile, get_feed, get_followers,
    get_following, is_following, get_alerts, search as be_search,
    new_alerts as be_new_alerts, delete_alert as be_delete_alert,
    remove_from_feed as be_rem_from_feed, update_profile_settings
)


users_bp = Blueprint('users', __name__)


@users_bp.app_template_filter('following')
def following_filter(_profile):
    """Checks if current user is following the user piped to filter."""
    return is_following(current_user.get('_id'), _profile.get('_id'))


@users_bp.app_template_filter('millify')
def millify_filter(n):
    """Template filter to millify numbers, e.g. 1K, 2M, 1.25B."""
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


@users_bp.app_template_filter('timeify')
def timeify_filter(time):
    """Takes integer epoch time and returns a DateTime string for display.

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


@users_bp.app_template_filter('datetime')
def datetime_filter(time):
    """Takes integer epoch time and returns a DateTime string for display."""
    return datetime.fromtimestamp(time).strftime('%Y-%m-%d %H:%M:%S')


@users_bp.app_template_filter('new_alerts')
def new_alerts_filter(user_id):
    """Check to see if the user has any alerts.

    .. warning: Should only ever really be used with ``current_user``.
    """
    return be_new_alerts(user_id)


@users_bp.route('/', methods=['GET'])
# Do not place login_required on this method handled by view for prettiness
def feed():
    """Displays the users feed or redirects the user to the signin if they are
    not already signed in.

    """
    if not current_user:
        return redirect(url_for('auth.signin'))

    # Pagination
    page = handle_page(request)
    # Get feed pagination
    pagination = get_feed(current_user.get('_id'), page,
                          current_user.get('feed_pagination_size'))

    # Post form
    post_form = PostForm()
    return render_template('feed.html', pagination=pagination,
                           post_form=post_form)


@users_bp.route('/feed/<post_id>/remove', methods=['POST'])
@login_required
def remove_from_feed(post_id):
    """Removes ``post_id`` from current users feed."""
    redirect_url = handle_next(request, url_for('users.feed'))

    if be_rem_from_feed(post_id, current_user.get('_id')):  # pragma: no branch
        flash('Message has been removed from feed', 'success')

    return redirect(handle_next(request, redirect_url))


@users_bp.route('/<username>', methods=['GET'])
@login_required
def profile(username):
    """It will show the users posts. Referred to as "posts" on the site."""
    uid = get_uid_username(username)

    if uid is None:
        abort(404)

    # Data
    _profile = get_profile(uid)

    # Pagination
    page = handle_page(request)
    # Get the posts pagination
    pagination = get_posts(uid, page,
                           current_user.get('feed_pagination_size'))

    # Post form
    post_form = PostForm()
    return render_template('posts.html', profile=_profile,
                           pagination=pagination, post_form=post_form)


@users_bp.route('/<username>/avatar', methods=['GET'])
@login_required
def avatar(username):
    """Return the users avatar image or the dafault."""
    # Get the user
    user = get_user(get_uid_username(username))

    # If the user has an avatar set then get it from GridFS
    if user.get('avatar') is not None:
        return get_upload(user.get('avatar'), cache_for=0,
                          collection='avatars')

    # The user doesn't have one send them the default
    return send_file('static/img/otter_avatar.png', cache_timeout=0)


@users_bp.route('/<username>/following', methods=['GET'])
@login_required
def following(username):
    """Returns all users following the current user as a pagination."""
    user_id = get_uid(username)

    if user_id is None:
        abort(404)

    # Data
    _profile = get_profile(user_id)

    # Pagination
    page = handle_page(request)

    # Get a list of users you are following
    _following = get_following(user_id, page,
                               current_user.get('feed_pagination_size'))

    # Post form
    post_form = PostForm()
    return render_template('following.html', profile=_profile,
                           pagination=_following, post_form=post_form)


@users_bp.route('/<username>/followers', methods=['GET'])
@login_required
def followers(username):
    """Returns all a users followers as a pagination object."""
    user_id = get_uid(username)

    if user_id is None:
        abort(404)

    # Data
    _profile = get_profile(user_id)

    # Pagination
    page = handle_page(request)

    # Get a list of users you are following
    _followers = get_followers(user_id, page,
                               current_user.get('feed_pagination_size'))

    # Post form
    post_form = PostForm()
    return render_template('followers.html', profile=_profile,
                           pagination=_followers, post_form=post_form)


@users_bp.route('/<username>/follow', methods=['POST'])
@login_required
def follow(username):
    """Follow a user."""
    redirect_url = handle_next(request, url_for('users.following',
                               username=current_user.get('username')))

    user_id = get_uid(username)

    # If we don't get a uid from the username the page doesn't exist
    if user_id is None:
        abort(404)

    # Unfollow user, ensure the user doesn't unfollow themself
    if user_id != current_user.get('_id'):
        if follow_user(current_user.get('_id'), user_id):
            flash('You have started following %s' % username, 'success')
    else:
        flash('You can\'t follow/unfollow yourself', 'information')

    return redirect(redirect_url)


@users_bp.route('/<username>/unfollow', methods=['POST'])
@login_required
def unfollow(username):
    """Unfollow a user"""
    redirect_url = handle_next(request, url_for('users.following',
                               username=current_user.get('username')))

    user_id = get_uid(username)

    # If we don't get a uid from the username the page doesn't exist
    if user_id is None:
        abort(404)

    # Unfollow user, ensure the user doesn't unfollow themself
    if user_id != current_user.get('_id'):
        if unfollow_user(current_user.get('_id'), user_id):
            flash('You are no longer following %s' % username, 'success')
    else:
        flash('You can\'t follow/unfollow yourself', 'information')

    return redirect(redirect_url)


@users_bp.route('/search', methods=['GET'])
@login_required
def search():
    """Search for a users. This is all done via a GET query.

    .. note: Should be _NO_ CSRF this will appear in the URL and look shit.
    """
    form = SearchForm(request.form)

    # Get the query string. If its not there return an empty string
    query = request.args.get('query', '')

    _results = be_search(query)
    return render_template('search.html', form=form, query=query,
                           pagination=_results)


@users_bp.route('/settings', methods=['GET', 'POST'])
@users_bp.route('/settings/profile', methods=['GET', 'POST'])
@login_required
def settings_profile():
    """Allows users to customize their profile direct from this view."""
    # Create the form and initialize the `select` field this can not be done
    # in the template.
    form = ChangeProfileForm(
        feed_pagination_size=(current_user.get('feed_pagination_size') or
                              app.config.get('FEED_ITEMS_PER_PAGE')),
        replies_pagination_size=(current_user.get('replies_pagination_size') or
                                 app.config.get('REPLIES_ITEMS_PER_PAGE')),
        alerts_pagination_size=(current_user.get('alerts_pagination_size') or
                                app.config.get('ALERT_ITEMS_PER_PAGE')),
        homepage=current_user.get('homepage', ''),
        location=current_user.get('location', '')
    )

    if request.method == 'POST':
        form = ChangeProfileForm()

        if form.validate():
            # If there is an uploaded File pass it on else pass nothing
            if form.upload.data:
                # Pass the BytesIO stream to the backend.
                upload = form.upload.data.stream
            else:
                upload = None

            # Update the current user in the session
            current_user['about'] = form.about.data
            current_user['hide_feed_images'] = form.hide_feed_images.data

            current_user['feed_pagination_size'] = \
                int(form.feed_pagination_size.data)
            current_user['replies_pagination_size'] = \
                int(form.replies_pagination_size.data)
            current_user['alerts_pagination_size'] = \
                int(form.alerts_pagination_size.data)

            current_user['homepage'] = form.homepage.data
            current_user['location'] = form.location.data

            # Update the user in the database
            user = update_profile_settings(
                current_user.get('_id'),
                about=form.about.data,
                hide_feed_images=form.hide_feed_images.data,
                feed_size=form.feed_pagination_size.data,
                replies_size=form.replies_pagination_size.data,
                alerts_size=form.alerts_pagination_size.data,
                homepage=form.homepage.data,
                location=form.location.data,
                upload=upload
            )

            # Reload the current_user
            current_user.update(user)

            flash('Your profile has been updated', 'success')
        else:
            flash('Oh no! There are errors in your form', 'error')

    return render_template('settings_profile.html', form=form)


@users_bp.route('/alerts', methods=['GET'])
@login_required
def alerts():
    """Display a users alerts (notifications) to them on the site."""
    uid = current_user.get('_id')

    # Pagination
    page = handle_page(request)

    _results = get_alerts(uid, page,
                          current_user.get('alerts_pagination_size'))
    return render_template('alerts.html', pagination=_results)


@users_bp.route('/alerts/<alert_id>/delete', methods=['GET'])
@login_required
def delete_alert(alert_id):
    """Remove an alert id (aid) from a users alerts feed."""
    user_id = current_user.get('_id')
    # Handle next
    redirect_url = handle_next(request, url_for('users.alerts'))

    if be_delete_alert(user_id, alert_id):
        flash('Alert has been hidden', 'success')

    return redirect(redirect_url)


@users_bp.route('/alerts/new', methods=['GET'])
def new_alerts():
    """Return a simple http status  response to denote if the current user has
    any alerts since last time this was called.

    This will be passed in with the template but will allow something an AJAX
    call to get the data also.

    .. note: See ``pjuu/static/js/alerts.js``
    """
    # We don't want this view to redirect to signin so we will throw a 403
    # this will make jQuery easier to use with this endpoint
    if not current_user:
        return abort(403)

    uid = current_user.get('_id')

    # If a user has alerts then return a 200 else a 404
    if be_new_alerts(uid):
        return "", 200
    return "", 404
