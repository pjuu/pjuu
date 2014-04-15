# -*- coding: utf8 -*-
# Stdlib
# 3rd party imports
from flask import (abort, flash, redirect, request,
                   url_for)
# Pjuu imports
from pjuu import app
from pjuu.auth.backend import current_user, get_uid
from pjuu.auth.decorators import login_required
from pjuu.lib import handle_next
from .backend import (create_post, create_comment, check_post,
                      vote as be_vote, has_voted, get_comment_author,
                      delete as be_delete)
from .forms import PostForm


@app.template_filter('voted')
def voted_filter(pid, cid=None):
    """
    Checks to see if current_user has voted on the post pid.

    To check a post simply:
        post.pid|voted
    To check a comment it is a little different:
        comment.pid|voted(comment.cid)

    These may be reffered to as items.X in lists.
    """
    vote = has_voted(current_user['uid'], pid, cid=cid)
    if vote is not None:
        vote = int(vote)
        if vote > 0:
            vote = "+" + str(vote)
    return vote


@app.route('/post', methods=['POST'])
@login_required
def post(redirect_url=None):
    """
    current_user creates a new post on Pjuu :)
    """
    redirect_url = handle_next(request,
        url_for('profile', username=current_user['username']))

    form = PostForm(request.form)
    if form.validate():
        pid = create_post(current_user['uid'], form.body.data)
        flash('Your post has been added', 'success')
    else:
        # This alert can handle only 1 form error
        flash(form.body.errors[0], 'error')
    return redirect(redirect_url)


@app.route('/<username>/<int:pid>/comment', methods=['POST'])
@login_required
def comment(username, pid):
    """
    current_user creates a comment of post 'pid' with the author 'username'
    """
    redirect_url = handle_next(request,
        url_for('view_post', username=username, pid=pid))

    form = PostForm(request.form)
    if form.validate():
        cid = create_comment(current_user['uid'], pid, form.body.data)
        flash('Your comment has been added', 'success')
    else:
        # This alert can handle only 1 form error
        flash(form.body.errors[0], 'error')

    return redirect(redirect_url)


@app.route('/<username>/<int:pid>/upvote', methods=['GET'])
@app.route('/<username>/<int:pid>/<int:cid>/upvote', methods=['GET'])
def upvote(username, pid=-1, cid=None):
    """
    Upvotes a post or comment.
    If this is a comment it _WILL_ update the comments authros score.
    The 'username' may seem a little confusing but the comment is on the
    'pid' which was created by 'username'.
    """
    redirect_url = handle_next(request,
        url_for('view_post', username=username, pid=pid))

    uid = get_uid(username)
    if not check_post(uid, pid, cid):
        return abort(404)

    # Don't allow a user to vote twice or vote on own post
    if not has_voted(current_user['uid'], pid, cid):
        if cid:
            result = be_vote(current_user['uid'], pid, cid, amount=1)
        else:
            result = be_vote(current_user['uid'], pid, amount=1)
        if not result:
            flash('You can not vote on your own posts', 'information')
    else:
        flash('You have already voted on this item', 'information')

    return redirect(redirect_url)


@app.route('/<username>/<int:pid>/downvote', methods=['GET'])
@app.route('/<username>/<int:pid>/<int:cid>/downvote', methods=['GET'])
def downvote(username, pid=-1, cid=None):
    """
    Downvotes a post or comment.
    If this is a comment it _WILL_ update the comments authros score.
    The 'username' may seem a little confusing but the comment is on the
    'pid' which was created by 'username'.
    """
    redirect_url = handle_next(request,
        url_for('view_post', username=username, pid=pid))

    uid = get_uid(username)
    if not check_post(uid, pid, cid):
        return abort(404)

    # Don't allow a user to vote twice or vote on own post
    if not has_voted(current_user['uid'], pid, cid):
        if cid:
            result = be_vote(current_user['uid'], pid, cid, amount=-1)
        else:
            result = be_vote(current_user['uid'], pid, amount=-1)
        if not result:
            flash('You can not vote on your own posts', 'information')
    else:
        flash('You have already voted on this item', 'information')

    return redirect(redirect_url)


@app.route('/<username>/<int:pid>/delete')
@app.route('/<username>/<int:pid>/<int:cid>/delete')
@login_required
def delete_post(username, pid, cid=None):
    """
    Deletes posts and comments.
    """
    redirect_url = handle_next(request, url_for('feed'))

    uid = get_uid(username)
    if not check_post(uid, pid, cid):
        return abort(404)

    if cid is not None:
        author_uid = get_comment_author(cid)
        if author_uid != int(current_user['uid']):
            return abort(403)
    else:
        if uid != int(current_user['uid']):
            return abort(403)

    # If you have made it here you can delete the post/comment
    # be_delete _WILL_ delete all the comments under a post if a post
    # is being deleted.
    be_delete(uid, pid, cid)

    if cid is not None:
        flash('Comment has been deleted', 'success')
    else:
        flash('Post has been deleted along with all comments', 'success')

    return redirect(redirect_url)
