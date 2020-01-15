# -*- coding: utf8 -*-

"""Flask endpoints for interacting with the posting system

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2020 Joe Doherty

"""

from flask import (abort, flash, redirect, request, url_for, render_template,
                   Blueprint, current_app as app, jsonify)
from jinja2 import escape

from pjuu.auth import current_user
from pjuu.auth.decorators import login_required
from pjuu.lib import handle_next, keys as k, timestamp, xflash
from pjuu.lib.pagination import handle_page
from pjuu.lib.uploads import get_upload as be_get_upload
from .backend import (create_post, check_post, has_voted, is_subscribed,
                      vote_post, get_post, delete_post as be_delete_post,
                      get_replies, unsubscribe as be_unsubscribe,
                      CantVoteOnOwn, AlreadyVoted, get_hashtagged_posts,
                      flag_post, has_flagged, CantFlagOwn, AlreadyFlagged,
                      unflag_post as be_unflag_post, get_global_feed)
from .forms import PostForm
from pjuu.auth.utils import get_user, get_uid
from pjuu.users.backend import get_user_permission


posts_bp = Blueprint('posts', __name__)


@posts_bp.app_template_filter('postify')
def postify_filter(post, limit_lines=False):
    """Will highlight everything that is stored along with the post: link,
    mentions and hash tags.

    To use on the post do the following:

    {% autoescape false %}
    post|postify
    {% endautoescape %}

    .. note: This does not work on the text but on the post so within templates
             you will need to use 'item|postify' and ensure autoescape is off.

    """
    post_body = post.get('body')

    items = post.get('links', []) + post.get('mentions', []) + \
        post.get('hashtags', [])

    items = sorted(items, key=lambda k: k['span'][0])

    offset = 0
    for item in items:
        left = item['span'][0] + offset
        right = item['span'][1] + offset

        # The snippet of text we need to replace
        replace_text = post_body[left:right]

        if 'link' in item:
            html = '<a href="{0}" target="_blank">{1}</a>'.format(
                item['link'],
                replace_text
            )

        elif 'username' in item:
            html = '<a href="{0}">{1}</a>'.format(
                url_for('users.profile', username=item['username']),
                replace_text
            )

        elif 'hashtag' in item:  # pragma: no branch
            # The pragma above is because the `else` should never be called
            html = '<a href="{0}">{1}</a>'.format(
                url_for('posts.hashtags', hashtag=item['hashtag']),
                replace_text
            )

        else:
            # Handles the can't happen case of there being and item that doesnt
            # match any of the above.
            continue  # pragma: no cover

        offset += len(html) - (item['span'][1] - item['span'][0])
        post_body = post_body[:left] + html + post_body[right:]

    if limit_lines:
        post_body = '\n'.join(post_body.splitlines()[:5])

    # Enable new lines to show
    post_body = post_body.replace("\n", "<br/>")

    return post_body


@posts_bp.app_template_filter('voted')
def voted_filter(post_id):
    """Checks to see if current_user has voted on the post pid.

    To check a post simply:
        item.post_id|voted

    These may be reffered to as items.X in lists.

    Will return 1 on upvote, -1 on downvote and 0 if not voted

    """
    if current_user:
        return has_voted(current_user.get('_id'), post_id) or 0
    return False


@posts_bp.app_template_filter('reversable')
def reversable_filter(vote):
    """The time voted `vote` has to be newer than VOTE_TIMEOUT

    """
    vote = 0 if not vote else vote
    return abs(vote) + k.VOTE_TIMEOUT > timestamp()


@posts_bp.app_template_filter('subscribed')
def subscribed_filter(post_id):
    """A simple filter to check if the current user is subscribed to a post

    """
    if current_user:
        return is_subscribed(current_user.get('_id'), post_id)
    return False


@posts_bp.app_template_filter('flagged')
def flagged_filter(post_id):
    """Check if a user flagged the post with post id"""
    if current_user:
        return has_flagged(current_user.get('_id'), post_id)
    return False


@posts_bp.route('/<username>/<post_id>', methods=['GET'])
def view_post(username, post_id):
    """Displays a post along with its comments paginated. I am not sure if this
    should be here or in the 'posts' app.

    .. note: Viewable to the public if the post is public!
    """
    if not check_post(get_uid(username), post_id):
        return abort(404)

    # Get post and comments for the current page
    _post = get_post(post_id)

    # Stop a reply from ever being shown here
    if 'reply_to' in _post:
        return abort(404)

    _user = get_user(get_uid(username))

    # Only get the permission if the post is not owned by the current user
    if current_user:
        current_user_id = current_user.get('_id')
    else:
        current_user_id = None

    permission = get_user_permission(_user.get('_id'), current_user_id)

    if permission < _post.get('permission', k.PERM_PUBLIC):
        return abort(403)

    # Pagination
    page = handle_page(request)

    # Handle explicit sort order
    # Fall back to user default else default
    sort = request.args.get('sort', None)
    if sort is None:
        if current_user:
            sort = current_user.get('reply_sort_order', -1)
        else:
            sort = -1
    else:
        try:
            sort = 1 if int(sort) > 0 else -1
        except ValueError:
            if current_user:
                sort = current_user.get('reply_sort_order', -1)
            else:
                sort = -1

    # Get the page sizes taking in to account non-logged in users
    if current_user:
        page_size = current_user.get(
            'replies_pagination_size',
            app.config.get('REPLIES_ITEMS_PER_PAGE', 25)
        )
    else:
        page_size = app.config.get('REPLIES_ITEMS_PER_PAGE', 25)

    pagination = get_replies(post_id, page, page_size, sort)

    post_form = PostForm()
    return render_template('view_post.html', post=_post,
                           pagination=pagination, post_form=post_form,
                           sort=sort)


@posts_bp.route('/post', methods=['GET', 'POST'])
@posts_bp.route('/<username>/<post_id>/reply', methods=['GET', 'POST'])
@login_required
def post(username=None, post_id=None):
    """Enabled current_user to create a new post on Pjuu :)

    This view accepts GET and POST yet only acts on a POST. This is so that the
    Werkzeug router does not treat this like a profile lookup.
    """
    # Rather than just 404 if someone tries to GET this URL (which is default),
    # we will throw a 405.
    if request.method == 'GET':
        return abort(405)

    # Stop un-approved users posting comments if permissions do not let them.
    if post_id is not None:
        if not check_post(get_uid(username), post_id):
            return abort(404)

        _post = get_post(post_id)

        # Ensuer user has permission to perform the action
        current_user_id = current_user.get('_id')
        permission = get_user_permission(_post.get('user_id'), current_user_id)

        if permission < _post.get('permission', k.PERM_PUBLIC):
            return abort(403)

    # Set the default redirect URLs depending on type of post it is
    if post_id is None:
        redirect_url = handle_next(request, url_for('users.profile',
                                   username=current_user['username']))
    else:
        redirect_url = handle_next(request, url_for('posts.view_post',
                                   username=username, post_id=post_id))

    # Stop muted users from creating posts
    if current_user.get('muted', False):
        flash('You have been silenced!', 'warning')
        return redirect(redirect_url)

    form = PostForm()
    if form.validate():
        # If there is an uploaded File pass it on else pass nothing
        if form.upload.data:
            # Pass the BytesIO stream to the backend.
            upload = form.upload.data.stream
        else:
            upload = None

        try:
            permission = int(form.permission.data)
        except ValueError:  # pragma: no cover
            permission = -1

        # WTForms should stop this ever, ever firing
        if not (k.PERM_PUBLIC <= permission <=  # pragma: no cover
                k.PERM_APPROVED):  # pragma: no cover
            flash('Invalid post permission set', 'error')
            return redirect(redirect_url)

        # Create the post
        if create_post(current_user['_id'], current_user['username'],
                       str(escape(form.body.data)), post_id, upload,
                       permission=permission):
            # Inform the user we have created the post
            flash('Your post has been added', 'success')
        else:
            flash('There was an error creating your post',
                  'error')  # pragma: no cover
    else:
        # Will print out all errors that happen in a post form.
        # This is better than "There is an error in your post"
        for key, value in form.errors.items():
            for error in value:
                flash(error, 'error')

    return redirect(redirect_url)


@posts_bp.route('/uploads/<path:filename>', methods=['GET'])
def get_upload(filename):
    """Simple function to get the uploaded content from GridFS.

    """
    return be_get_upload(filename)


@posts_bp.route('/<username>/<post_id>/upvote', methods=['POST'],
                endpoint='upvote')
@posts_bp.route('/<username>/<post_id>/<reply_id>/upvote', methods=['POST'],
                endpoint='upvote')
@posts_bp.route('/<username>/<post_id>/downvote', methods=['POST'],
                endpoint='downvote')
@posts_bp.route('/<username>/<post_id>/<reply_id>/downvote', methods=['POST'],
                endpoint='downvote')
@login_required
def vote(username, post_id, reply_id=None):
    """Upvotes a post.

    .. note: If the request is an XHR one the whole function will not run.
             It will exit out and the first chance and return JSON.
    """
    redirect_url = handle_next(request, url_for('posts.view_post',
                               username=username, post_id=post_id))

    if not check_post(get_uid(username), post_id, reply_id):
        if request.is_xhr:
            return jsonify({'message': 'Post not found'}), 404

        return abort(404)

    _post = get_post(post_id)

    # Ensuer user has permission to perform the action
    current_user_id = current_user.get('_id')
    permission = get_user_permission(_post.get('user_id'), current_user_id)

    # Since the upvote/downvote functions have been merged we need to
    # identify which action is going to be performed.
    if request.endpoint == 'posts.upvote':
        action = 'upvoted'
        amount = 1
    else:
        action = 'downvoted'
        amount = -1

    if permission < _post.get('permission', k.PERM_PUBLIC):
        message = 'You do not have permission to vote on this post'

        if request.is_xhr:
            return jsonify({'message': message}), 403

        xflash(message, 'error')
        return redirect(redirect_url)

    try:
        if reply_id is None:
            result = vote_post(current_user['_id'], post_id, amount=amount)
        else:
            result = vote_post(current_user['_id'], reply_id, amount=amount)
    except AlreadyVoted:
        message = 'You have already voted on this post'

        if request.is_xhr:
            return jsonify({'message': message}), 400

        xflash(message, 'error')
    except CantVoteOnOwn:
        message = 'You can not vote on your own posts'

        if request.is_xhr:
            return jsonify({'message': message}), 400

        xflash(message, 'error')
    else:
        if (amount > 0 < result) or (amount < 0 > result):
            message = 'You {} the '.format(action) + ("comment" if reply_id
                                                      else "post")
            xflash(message, 'success')
        else:
            message = 'You reversed your vote on the ' + ("comment" if reply_id
                                                          else "post")
            xflash(message, 'success')

    if request.is_xhr:
        return jsonify({'message': message}), 200

    return redirect(redirect_url)


@posts_bp.route('/<username>/<post_id>/delete', methods=['POST'])
@posts_bp.route('/<username>/<post_id>/<reply_id>/delete', methods=['POST'])
@login_required
def delete_post(username, post_id, reply_id=None):
    """Deletes posts.

    """
    # The default redirect is different for a post/reply deletion
    # Reply deletion keeps you on the page and post deletion takes you to feed
    if reply_id is not None:
        redirect_url = handle_next(request, url_for('posts.view_post',
                                   username=username, post_id=post_id))
    else:
        redirect_url = handle_next(request, url_for('users.feed'))

    user_id = get_uid(username)
    if not check_post(user_id, post_id, reply_id):
        return abort(404)

    if reply_id is not None:
        _post = get_post(reply_id)

        if _post['user_id'] != current_user['_id'] and \
                user_id != current_user['_id']:
            return abort(403)
    else:
        if user_id != current_user['_id']:
            return abort(403)

    if reply_id is not None:
        be_delete_post(reply_id)
        flash('Post has been deleted', 'success')
    else:
        be_delete_post(post_id)
        flash('Post has been deleted along with all replies', 'success')

    return redirect(redirect_url)


@posts_bp.route('/<username>/<post_id>/unsubscribe', methods=['POST'])
@login_required
def unsubscribe(username, post_id):
    """Unsubscribes a user from a post

    """
    if not check_post(get_uid(username), post_id):
        return abort(404)

    # The default URL is to go back to the posts view
    redirect_url = handle_next(request, url_for('posts.view_post',
                               username=username, post_id=post_id))

    # Unsubscribe the user from the post, only show them a message if they
    # were actually unsubscribed
    if be_unsubscribe(current_user['_id'], post_id):
        flash('You have been unsubscribed from this post', 'success')

    return redirect(redirect_url)


@posts_bp.route('/<username>/<post_id>/flag', methods=['POST'])
@login_required
def flag(username, post_id):
    """Flags a post so that moderators are aware of it.

    .. note: This is a requirement to enter the Apple app store.
    """
    if not check_post(get_uid(username), post_id):
        return abort(404)

    _post = get_post(post_id)

    # Ensure the default redirect is to the correct location.
    reply_id = get_post(post_id).get('reply_to')

    if reply_id is None:
        redirect_url = handle_next(request, url_for('posts.view_post',
                                   username=username, post_id=post_id))
    else:
        reply = get_post(reply_id)
        redirect_url = handle_next(request, url_for('posts.view_post',
                                   username=reply.get('username'),
                                   post_id=reply_id))

    # Ensue user has permission to perform the action
    current_user_id = current_user.get('_id')
    permission = get_user_permission(_post.get('user_id'), current_user_id)

    if permission < _post.get('permission', k.PERM_PUBLIC):
        flash('You do not have permission to flag this post',
              'error')
        return redirect(redirect_url)

    try:
        flag_post(current_user['_id'], post_id)
    except CantFlagOwn:
        flash('You can not flag on your own posts', 'error')
    except AlreadyFlagged:
        flash('You have already flagged this post', 'error')
    else:
        flash('You flagged the ' + ('comment' if reply_id else 'post'),
              'success')

    return redirect(redirect_url)


@posts_bp.route('/dashboard/<post_id>/unflag', methods=['GET'])
def unflag_post(post_id):
    """Resets a posts votes to 0.

    .. note: OP users only. Uses a `dashboard URL`
    """
    # Do not allow users who are not OP to log in
    if not current_user or not current_user.get('op', False):
        return abort(403)

    if get_post(post_id) is None:
        return abort(404)

    # Reset the posts flag. Doesn't matter if there aren't any
    be_unflag_post(post_id)
    flash('Flags have been reset for post', 'success')

    # Always go back to the dashboard
    redirect_url = url_for('dashboard.dashboard')

    return redirect(redirect_url)


@posts_bp.route('/hashtags', methods=['GET'])
@posts_bp.route('/hashtags/<hashtag>', methods=['GET'])
@login_required
def hashtags(hashtag=None):
    """Used to view a list of posts which contain a specific hashtag.

    """
    # We need to check the conditions for a valid hashtag if not we will
    # perform a 404 ourselves.
    if not hashtag or len(hashtag) < 2:
        return abort(404)

    # Pagination
    page = handle_page(request)
    pagination = get_hashtagged_posts(hashtag.lower(), page)

    return render_template('hashtags.html', hashtag=hashtag,
                           pagination=pagination)


@posts_bp.route('/global', methods=['GET'])
def global_feed():
    """Show a weighted list of public/pjuu only posts depending if the user is
    logged in or not
    """
    if current_user:
        page_size = current_user.get('feed_pagination_size',
                                     app.config.get('FEED_ITEMS_PER_PAGE', 25))
    else:
        page_size = app.config.get('FEED_ITEMS_PER_PAGE', 25)

    if current_user:
        permission = 1
    else:
        permission = 0

    page = handle_page(request)

    _posts = get_global_feed(page, page_size, perm=permission)

    post_form = PostForm()
    return render_template('global_feed.html', pagination=_posts,
                           post_form=post_form)
