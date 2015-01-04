# -*- coding: utf8 -*-

"""
Description:
    The actual Flask endpoints for the posts system.

Licence:
    Copyright 2014-2015 Joe Doherty <joe@pjuu.com>

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
from flask import current_app as app, abort, flash, redirect, request, url_for
# Pjuu imports
from pjuu.auth import current_user
from pjuu.auth.backend import get_uid, is_mute
from pjuu.auth.decorators import login_required
from pjuu.lib import handle_next
from .backend import (create_post, create_comment, check_post, has_voted,
                      get_comment_author, is_subscribed, vote_post,
                      vote_comment, delete_post as be_delete_post,
                      delete_comment as be_delete_comment,
                      unsubscribe as be_unsubscribe, CantVoteOnOwn,
                      AlreadyVoted)
from .forms import PostForm


@app.template_filter('voted')
def voted_filter(xid, comment=False):
    """
    Checks to see if current_user has voted on the post pid.

    To check a post simply:
        item.pid|voted
    To check a comment it is a little different:
        item.cid|voted(True)

    These may be reffered to as items.X in lists.

    Will return 1 on upvote, -1 on downvote and 0 if not voted
    """
    return has_voted(current_user['uid'], xid, comment=comment) or 0


@app.template_filter('subscribed')
def subscribed_filter(pid):
    """
    A simple filter to check if the current user is subscribed to a post
    """
    return is_subscribed(current_user['uid'], pid)


@app.route('/post', methods=['GET', 'POST'])
@login_required
def post(redirect_url=None):
    """
    current_user creates a new post on Pjuu :)

    This view accepts GET and POST yet only acts on a POST. This is so that the
    Werkzeug router does not treat this like a profile lookup
    """
    # Rather than just 404 if someone tries to GET this URL which is default
    # if we don't specify it we will throw a 405.
    if request.method == 'GET':
        return abort(405)

    redirect_url = handle_next(request, url_for('profile',
                               username=current_user['username']))

    # Stop muted users from creating posts
    if is_mute(current_user['uid']):
        flash('You have been silenced!', 'warning')
        return redirect(redirect_url)

    form = PostForm(request.form)
    if form.validate():
        pid = create_post(current_user['uid'], form.body.data)
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


@app.route('/<username>/<pid>/comment', methods=['GET', 'POST'])
@login_required
def comment(username, pid):
    """
    current_user creates a comment of post 'pid' with the author 'username'
    """
    # Rather than just 404 if someone tries to GET this URL which is default
    # if we don't specify it we will throw a 405.
    if request.method == 'GET':
        return abort(405)

    redirect_url = handle_next(request, url_for('view_post',
                               username=username, pid=pid))

    # Stop muted users from commenting
    if is_mute(current_user['uid']):
        flash('You have been silenced!', 'warning')
        return redirect(redirect_url)

    form = PostForm(request.form)
    if form.validate():
        cid = create_comment(current_user['uid'], pid, form.body.data)
        flash('Your comment has been added', 'success')
    else:
        # This flash can handle only 1 form error
        # There is an odd issue where are error is thrown with no errors
        # Can't recreate the issue
        if len(form.body.errors) > 0:
            flash(form.body.errors[0], 'error')
        else:
            flash('Oh no! There are errors in your comment.',
                  'error')  # pragma: no cover
    return redirect(redirect_url)


@app.route('/<username>/<pid>/upvote', methods=['GET'])
@app.route('/<username>/<pid>/<cid>/upvote', methods=['GET'])
@login_required
def upvote(username, pid=-1, cid=None):
    """
    Upvotes a post or comment.
    If this is a comment it _WILL_ update the comments authros score.
    The 'username' may seem a little confusing but the comment is on the
    'pid' which was created by 'username'.
    """
    redirect_url = handle_next(request, url_for('view_post',
                               username=username, pid=pid))

    uid = get_uid(username)
    if not check_post(uid, pid, cid):
        return abort(404)

    try:
        if cid:
            result = vote_comment(current_user['uid'], cid, amount=1)
        else:
            result = vote_post(current_user['uid'], pid, amount=1)
    except AlreadyVoted:
        flash('You have already voted on this post', 'error')
    except CantVoteOnOwn:
        flash('You can not vote on your own posts', 'error')
    else:
        flash('You upvoted the post', 'success')

    return redirect(redirect_url)


@app.route('/<username>/<pid>/downvote', methods=['GET'])
@app.route('/<username>/<pid>/<cid>/downvote', methods=['GET'])
@login_required
def downvote(username, pid=-1, cid=None):
    """
    Downvotes a post or comment.
    If this is a comment it _WILL_ update the comments authros score.
    The 'username' may seem a little confusing but the comment is on the
    'pid' which was created by 'username'.
    """
    redirect_url = handle_next(request, url_for('view_post',
                               username=username, pid=pid))

    uid = get_uid(username)
    if not check_post(uid, pid, cid):
        return abort(404)

    try:
        if cid:
            result = vote_comment(current_user['uid'], cid, amount=-1)
        else:
            result = vote_post(current_user['uid'], pid, amount=-1)
    except AlreadyVoted:
        flash('You have already voted on this post', 'error')
    except CantVoteOnOwn:
        flash('You can not vote on your own posts', 'error')
    else:
        flash('You downvoted the post', 'success')

    return redirect(redirect_url)


@app.route('/<username>/<pid>/delete', methods=['GET'])
@app.route('/<username>/<pid>/<cid>/delete', methods=['GET'])
@login_required
def delete_post(username, pid, cid=None):
    """
    Deletes posts and comments.
    """
    # The default redirect is different for a post/comment deletion
    # Comment deletion keeps you on the page and post deletion takes you
    # to your feed
    if cid is not None:
        redirect_url = handle_next(request, url_for('view_post',
                                   username=username, pid=pid))
    else:
        redirect_url = handle_next(request, url_for('feed'))

    uid = get_uid(username)
    if not check_post(uid, pid, cid):
        return abort(404)

    if cid is not None:
        author_uid = get_comment_author(cid)
        # Allow not only the comment author to remove the comment but also
        # allow the post author to do so!
        if author_uid != current_user['uid'] and \
           uid != current_user['uid']:
            return abort(403)
    else:
        # If this is a post ONLY allow the post author to delete
        if uid != current_user['uid']:
            return abort(403)

    if cid is not None:
        be_delete_comment(cid)
        flash('Comment has been deleted', 'success')
    else:
        be_delete_post(pid)
        flash('Post has been deleted along with all comments', 'success')

    return redirect(redirect_url)


@app.route('/<username>/<pid>/unsubscribe')
@login_required
def unsubscribe(username, pid):
    """
    Unsubscribes a user from a post
    """
    # The default URL is to go back to the posts view
    redirect_url = handle_next(request, url_for('view_post',
                               username=username, pid=pid))

    uid = get_uid(username)
    if not check_post(uid, pid):
        return abort(404)

    # Unsubscribe the user from the post, only show them a message if they
    # were actually unsubscribed
    if be_unsubscribe(current_user['uid'], pid):
        flash('You have been unsubscribed from this post', 'success')

    return redirect(redirect_url)
