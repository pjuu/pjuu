# Stdlib
from datetime import datetime
# 3rd party imports
from flask import (abort, flash, g, redirect, render_template, request,
                   session, url_for)
# Pjuu imports
from pjuu import app
from pjuu.auth.backend import current_user, is_safe_url
from pjuu.auth.decorators import login_required
from .backend import (create_post, create_comment, get_post_full)
from .forms import PostForm


@app.route('/post', methods=['POST'])
@login_required
def post():
    redirect_url = request.values.get('next', None)
    if not redirect_url or not is_safe_url(redirect_url):
        redirect_url=url_for('profile', username=current_user.username)

    form = PostForm(request.form)
    if form.validate():
        pid = create_post(current_user['uid'], form.body.data)
        flash('Posted #%d' % pid, 'success')
    else:
        flash('Please enter something to post', 'error')
    return redirect(redirect_url)


@app.route('/<username>/<int:pid>/comment', methods=['POST'])
@login_required
def comment(username, pid):
    form = PostForm(request.form)
    if form.validate():
        cid = Comment(current_user['uid'], pid, form.body.data)
        flash('Commented #%d' % cid, 'success')
    else:
        flash('You need to type something to post.', 'error')
    return redirect(url_for('view_post', username=username, post_id=post.id))


@app.route('/<username>/<int:pid>')
@login_required
def view_post(username, pid):
    post_form = PostForm()
    return render_template('posts/post.html', user=user, post=post,
                           post_form=post_form)


@app.route('/<username>/<int:pid>/upvote', methods=['GET'])
@app.route('/<username>/<int:pid>/<int:cid>/upvote', methods=['GET'])
def upvote(username, pid, cid=None):
    return "UPVOTED"


@app.route('/<username>/<int:pid>/downvote', methods=['GET'])
@app.route('/<username>/<int:pid>/<int:cid>/downvote', methods=['GET'])
def downvote(username, pid, cid=None):
    return "DOWNVOTED"


@app.route('/<username>/<int:pid>/delete')
@app.route('/<username>/<int:pid>/<int:cid>/delete')
@login_required
def delete_post(username, pid, cid=None):
    return "DELETED"
