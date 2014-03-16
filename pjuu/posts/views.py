# -*- coding: utf8 -*-
# Stdlib
# 3rd party imports
from flask import (abort, flash, redirect, request,
                   url_for)
# Pjuu imports
from pjuu import app
from pjuu.auth.backend import current_user, is_safe_url, get_uid
from pjuu.auth.decorators import login_required
from .backend import (create_post, create_comment, check_post,
                      downvote as be_downvote, upvote as be_upvote,
                      has_voted)
from .forms import PostForm


@app.template_filter('voted')
def voted_filter(pid, cid=None):
    """
    Checks if current user is following the user with id piped to filter
    """
    vote = has_voted(current_user['uid'], pid, cid=cid)
    if vote is not None:
        vote = int(vote)
        if vote == 1:
            vote = "+1"
    return vote


@app.route('/post', methods=['POST'])
@login_required
def post():
    # Handle 'next' query string variable
    redirect_url = request.values.get('next', None)
    if not redirect_url or not is_safe_url(redirect_url):
        redirect_url = url_for('profile', username=current_user['username'])

    form = PostForm(request.form)
    if form.validate():
        pid = create_post(current_user['uid'], form.body.data)
        flash('Your post has been added', 'success')
    else:
        flash('That\'s a pointless post', 'error')
    return redirect(redirect_url)


@app.route('/<username>/<int:pid>/comment', methods=['POST'])
@login_required
def comment(username, pid):
    form = PostForm(request.form)
    if form.validate():
        cid = create_comment(current_user['uid'], pid, form.body.data)
        flash('Your comment has been added', 'success')
    else:
        flash('That\'s a pointless comment', 'error')
    return redirect(url_for('view_post', username=username, pid=pid))


@app.route('/<username>/<int:pid>/upvote', methods=['GET'])
@app.route('/<username>/<int:pid>/<int:cid>/upvote', methods=['GET'])
def upvote(username, pid=-1, cid=None):
    """
    Upvotes a post or comment.
    """
    uid = get_uid(username)
    if not check_post(uid, pid, cid):
        return abort(404)

    redirect_url = request.values.get('next', None)
    if not redirect_url or not is_safe_url(redirect_url):
        redirect_url = url_for('view_post', username=username, pid=pid)

    # Don't allow a user to vote twice or vote on own post
    if not has_voted(current_user['uid'], pid, cid):
        if cid:
            be_upvote(current_user['uid'], pid, cid)
        else:
            be_upvote(current_user['uid'], pid)
    else:
        flash('You have already voted on this item', 'information')

    return redirect(redirect_url)


@app.route('/<username>/<int:pid>/downvote', methods=['GET'])
@app.route('/<username>/<int:pid>/<int:cid>/downvote', methods=['GET'])
def downvote(username, pid=-1, cid=None):
    """
    Downvotes a post or comment.
    """
    uid = get_uid(username)
    if not check_post(uid, pid, cid):
        return abort(404)

    redirect_url = request.values.get('next', None)
    if not redirect_url or not is_safe_url(redirect_url):
        redirect_url = url_for('view_post', username=username, pid=pid)

    # Don't allow a user to vote twice
    if not has_voted(current_user['uid'], pid, cid):
        if cid:
            be_downvote(current_user['uid'], pid, cid)
        else:
            be_downvote(current_user['uid'], pid)
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
    pass