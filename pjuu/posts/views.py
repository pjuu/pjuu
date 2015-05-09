# -*- coding: utf8 -*-

"""Flask endpoints for interacting with the posting system

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2015 Joe Doherty

"""

from flask import (abort, flash, redirect, request, url_for, render_template,
                   Blueprint)

from pjuu.auth import current_user
from pjuu.auth.utils import get_uid
from pjuu.auth.decorators import login_required
from pjuu.lib import handle_next
from pjuu.lib.pagination import handle_page
from pjuu.lib.uploads import get_upload as be_get_upload
from .backend import (create_post, check_post, has_voted, is_subscribed,
                      vote_post, get_post, delete_post as be_delete_post,
                      get_replies, unsubscribe as be_unsubscribe,
                      CantVoteOnOwn, AlreadyVoted, get_hashtagged_posts)
from .forms import PostForm


posts_bp = Blueprint('posts', __name__)


@posts_bp.app_template_filter('postify')
def postify_filter(post):
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

        elif 'hashtag' in item:
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

    return post_body


@posts_bp.app_template_filter('voted')
def voted_filter(post_id):
    """Checks to see if current_user has voted on the post pid.

    To check a post simply:
        item.post_id|voted

    These may be reffered to as items.X in lists.

    Will return 1 on upvote, -1 on downvote and 0 if not voted

    """
    return has_voted(current_user.get('_id'), post_id) or 0


@posts_bp.app_template_filter('subscribed')
def subscribed_filter(post_id):
    """A simple filter to check if the current user is subscribed to a post

    """
    return is_subscribed(current_user.get('_id'), post_id)


@posts_bp.route('/<username>/<post_id>', methods=['GET'])
@login_required
def view_post(username, post_id):
    """
    Displays a post along with its comments paginated. I am not sure if this
    should be here or in the 'posts' app.
    """
    if not check_post(get_uid(username), post_id):
        return abort(404)

    # Pagination
    page = handle_page(request)

    # Get post and comments for the current page
    _post = get_post(post_id)

    # Stop a reply from ever being shown here
    if 'reply_to' in _post:
        return abort(404)

    pagination = get_replies(post_id, page)

    post_form = PostForm()
    return render_template('view_post.html', post=_post,
                           pagination=pagination, post_form=post_form)


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

        # Create the post
        if create_post(current_user['_id'], current_user['username'],
                       form.body.data, post_id, upload):
            # Inform the user we have created the post
            flash('Your post has been added', 'success')
        else:
            flash('There was an error creating your post',
                  'error')  # pragma: no cover
    else:
        # Will print out all errors that happen in a post form.
        # This is better than "There is an error in your post"
        for key, value in form.errors.iteritems():
            for error in value:
                flash(error, 'error')

    return redirect(redirect_url)


@posts_bp.route('/uploads/<path:filename>', methods=['GET'])
@login_required
def get_upload(filename):
    """Simple function to get the uploaded content from GridFS.

    """
    return be_get_upload(filename)


@posts_bp.route('/<username>/<post_id>/upvote', methods=['GET'])
@posts_bp.route('/<username>/<post_id>/<reply_id>/upvote', methods=['GET'])
@login_required
def upvote(username, post_id, reply_id=None):
    """Upvotes a post.

    """
    redirect_url = handle_next(request, url_for('posts.view_post',
                               username=username, post_id=post_id))

    user_id = get_uid(username)
    if not check_post(user_id, post_id, reply_id):
        return abort(404)

    try:
        if reply_id is None:
            vote_post(current_user['_id'], post_id, amount=1)
        else:
            vote_post(current_user['_id'], reply_id, amount=1)
    except AlreadyVoted:
        flash('You have already voted on this post', 'error')
    except CantVoteOnOwn:
        flash('You can not vote on your own posts', 'error')
    else:
        flash('You upvoted the ' + (
                                    "comment" if reply_id else "post"),
              'success')

    return redirect(redirect_url)


@posts_bp.route('/<username>/<post_id>/downvote', methods=['GET'])
@posts_bp.route('/<username>/<post_id>/<reply_id>/downvote', methods=['GET'])
@login_required
def downvote(username, post_id, reply_id=None):
    """Downvotes a post.

    """
    redirect_url = handle_next(request, url_for('posts.view_post',
                               username=username, post_id=post_id))

    user_id = get_uid(username)
    if not check_post(user_id, post_id, reply_id):
        return abort(404)

    try:
        if reply_id is None:
            vote_post(current_user['_id'], post_id, amount=-1)
        else:
            vote_post(current_user['_id'], reply_id, amount=-1)
    except AlreadyVoted:
        flash('You have already voted on this post', 'error')
    except CantVoteOnOwn:
        flash('You can not vote on your own posts', 'error')
    else:
        flash('You downvoted the ' + (
                                      "comment" if reply_id else "post"),
              'success')

    return redirect(redirect_url)


@posts_bp.route('/<username>/<post_id>/delete', methods=['GET'])
@posts_bp.route('/<username>/<post_id>/<reply_id>/delete', methods=['GET'])
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


@posts_bp.route('/<username>/<post_id>/unsubscribe', methods=['GET'])
@login_required
def unsubscribe(username, post_id):
    """Unsubscribes a user from a post

    """
    # The default URL is to go back to the posts view
    redirect_url = handle_next(request, url_for('posts.view_post',
                               username=username, post_id=post_id))

    user_id = get_uid(username)
    if not check_post(user_id, post_id):
        return abort(404)

    # Unsubscribe the user from the post, only show them a message if they
    # were actually unsubscribed
    if be_unsubscribe(current_user['_id'], post_id):
        flash('You have been unsubscribed from this post', 'success')

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
