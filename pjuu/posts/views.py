# -*- coding: utf8 -*-

"""
Description:
    The Flask endpoints for the posts system.

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

# 3rd party imports
from flask import (current_app as app, abort, flash, redirect, request,
                   url_for, render_template)
# Pjuu imports
from pjuu.auth import current_user
from pjuu.auth.backend import get_uid
from pjuu.auth.decorators import login_required
from pjuu.lib import handle_next
from pjuu.lib.pagination import handle_page
from .backend import (create_post, check_post, has_voted, is_subscribed,
                      vote_post, get_post, delete_post as be_delete_post,
                      get_replies, unsubscribe as be_unsubscribe,
                      CantVoteOnOwn, AlreadyVoted, parse_tags)
from .forms import PostForm


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
        link = '<a href=\"/{0}\">{1}</a>'.format(tag[1], tag[2])
        # Calculate the offset to adjust rest of tag boundries
        offset += len(link) - len(tag[2])
        # Add the link in place of the '@' tag
        body = (body[:left] + link + body[right:])
    return body


@app.template_filter('voted')
def voted_filter(post_id):
    """Checks to see if current_user has voted on the post pid.

    To check a post simply:
        item.post_id|voted

    These may be reffered to as items.X in lists.

    Will return 1 on upvote, -1 on downvote and 0 if not voted

    """
    return has_voted(current_user.get('_id'), post_id) or 0


@app.template_filter('subscribed')
def subscribed_filter(post_id):
    """A simple filter to check if the current user is subscribed to a post

    """
    return is_subscribed(current_user.get('_id'), post_id)


@app.route('/<username>/<post_id>', methods=['GET'])
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
    post = get_post(post_id)
    pagination = get_replies(post_id, page)

    post_form = PostForm()
    return render_template('view_post.html', post=post,
                           pagination=pagination, post_form=post_form)


@app.route('/post', methods=['GET', 'POST'])
@app.route('/<username>/<reply_to>/post', methods=['GET', 'POST'],
           endpoint="reply")
@login_required
def post(username=None, reply_to=None):
    """Enabled current_user to create a new post on Pjuu :)

    This view accepts GET and POST yet only acts on a POST. This is so that the
    Werkzeug router does not treat this like a profile lookup.

    """
    # Rather than just 404 if someone tries to GET this URL (which is default),
    # we will throw a 405.
    if request.method == 'GET':
        return abort(405)

    # Set the default redirect URLs depending on type of post it is
    if reply_to is None:
        redirect_url = handle_next(request, url_for('profile',
                                   username=current_user['username']))
    else:
        redirect_url = handle_next(request, url_for('view_post',
                                   username=username, post_id=reply_to))

    # Stop muted users from creating posts
    if current_user.get('muted', False):
        flash('You have been silenced!', 'warning')
        return redirect(redirect_url)

    form = PostForm(request.form)
    if form.validate():
        # Create the post
        if create_post(current_user['_id'], current_user['username'],
                       form.body.data, reply_to):
            # Inform the user we have created the post
            flash('Your post has been added', 'success')
    else:
        # This flash can handle only 1 form error
        # There is an odd issue where are error is thrown with no errors
        # Can't recreate the issue
        if len(form.body.errors) > 0:
            flash(form.body.errors[0], 'error')
        else:
            flash('Oh no! There are errors in your post.',
                  'error')  # pragma: no cover
    return redirect(redirect_url)


@app.route('/<username>/<post_id>/upvote', methods=['GET'])
@app.route('/<username>/<post_id>/<reply_id>/upvote', methods=['GET'])
@login_required
def upvote(username, post_id, reply_id=None):
    """Upvotes a post.

    """
    redirect_url = handle_next(request, url_for('view_post',
                               username=username, post_id=post_id))

    user_id = get_uid(username)
    if not check_post(user_id, post_id, reply_id):
        return abort(404)

    try:
        vote_post(current_user['_id'], post_id, amount=1)
    except AlreadyVoted:
        flash('You have already voted on this post', 'error')
    except CantVoteOnOwn:
        flash('You can not vote on your own posts', 'error')
    else:
        flash('You upvoted the post', 'success')

    return redirect(redirect_url)


@app.route('/<username>/<post_id>/downvote', methods=['GET'])
@app.route('/<username>/<post_id>/<reply_id>/downvote', methods=['GET'])
@login_required
def downvote(username, post_id, reply_id=None):
    """Downvotes a post.

    """
    redirect_url = handle_next(request, url_for('view_post',
                               username=username, post_id=post_id))

    user_id = get_uid(username)
    if not check_post(user_id, post_id, reply_id):
        return abort(404)

    try:
        vote_post(current_user['_id'], post_id, amount=-1)
    except AlreadyVoted:
        flash('You have already voted on this post', 'error')
    except CantVoteOnOwn:
        flash('You can not vote on your own posts', 'error')
    else:
        flash('You upvoted the post', 'success')

    return redirect(redirect_url)


@app.route('/<username>/<post_id>/delete', methods=['GET'])
@app.route('/<username>/<post_id>/<reply_id>/delete', methods=['GET'])
@login_required
def delete_post(username, post_id, reply_id=None):
    """Deletes posts.

    """
    # The default redirect is different for a post/comment deletion
    # Comment deletion keeps you on the page and post deletion takes you
    # to your feed
    if reply_id is not None:
        redirect_url = handle_next(request, url_for('view_post',
                                   username=username, pid=post_id))
    else:
        redirect_url = handle_next(request, url_for('feed'))

    user_id = get_uid(username)
    if not check_post(user_id, post_id, reply_id):
        return abort(404)

    if reply_id is not None:
        post = get_post(reply_id)
    else:
        post = get_post(post_id)

    if post.get('username') == current_user['username'] or \
            post.get('username') == username:
        be_delete_post(post.get('_id'))

        flash('Post has been deleted', 'success')

    return redirect(redirect_url)


@app.route('/<username>/<post_id>/unsubscribe')
@login_required
def unsubscribe(username, post_id):
    """Unsubscribes a user from a post

    """
    # The default URL is to go back to the posts view
    redirect_url = handle_next(request, url_for('view_post',
                               username=username, pid=post_id))

    user_id = get_uid(username)
    if not check_post(user_id, post_id):
        return abort(404)

    # Unsubscribe the user from the post, only show them a message if they
    # were actually unsubscribed
    if be_unsubscribe(current_user['_id'], post_id):
        flash('You have been unsubscribed from this post', 'success')

    return redirect(redirect_url)
