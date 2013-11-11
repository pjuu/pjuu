# 3rd party imports
from flask import (abort, flash, g, redirect, render_template, request,
                   session, url_for)
# Pjuu imports
from pjuu import app, db
from pjuu.auth.backend import current_user, is_safe_url
from pjuu.auth.decorators import login_required
from pjuu.users.models import User
from .forms import PostForm
from .models import Comment, Post


@app.route('/post', methods=['POST'])
@login_required
def post():
    redirect_url = request.values.get('next', None)
    if not redirect_url or not is_safe_url(redirect_url):
        redirect_url=url_for('profile', username=current_user.username)

    form = PostForm(request.form)
    if form.validate():
        new_post = Post(current_user, form.body.data)
        db.session.add(new_post)
        db.session.commit()
        flash('Posted', 'success')
    else:
        flash('Please enter something to post', 'error')
    return redirect(redirect_url)


@app.route('/<username>/<int:post_id>/comment', methods=['POST'])
@login_required
def comment(username, post_id):
    form = PostForm(request.form)
    # Check that the post_id matches up with that of the user
    user = User.query.filter_by(username=username).first()
    post = Post.query.get(post_id)
    if not user or not post or post.user is not user:
        abort(404)

    if form.validate():
        new_comment = Comment(current_user, post_id, form.body.data)
        db.session.add(new_comment)
        db.session.commit()
        flash('Comment posted', 'success')
    else:
        flash('You need to type something to post.', 'error')
    return redirect(url_for('view_post', username=username, post_id=post.id))


@app.route('/<username>/<int:post_id>')
@login_required
def view_post(username, post_id):
    post = Post.query.get(post_id)
    user = User.query.filter_by(username=username).first()

    if not user or not post or post.user is not user:
        abort(404)

    post_form = PostForm()
    return render_template('posts/post.html', user=user, post=post,
                           post_form=post_form)


@app.route('/<username>/<int:post_id>/upvote', methods=['GET'])
@app.route('/<username>/<int:post_id>/<int:comment_id>/upvote', methods=['GET'])
def upvote(username, post_id, comment_id=None):
    pass


@app.route('/<username>/<int:post_id>/downvote', methods=['GET'])
@app.route('/<username>/<int:post_id>/<int:comment_id>/downvote', methods=['GET'])
def downvote(username, post_id, comment_id=None):
    pass


@app.route('/<username>/<int:post_id>/delete')
@app.route('/<username>/<int:post_id>/<int:comment_id>/delete')
@login_required
def delete_post(username, post_id, comment_id=None):
    post = Post.query.get(post_id)
    user = User.query.filter_by(username=username).first()    
    if comment_id:
        # Handle comment deletes
        comment = Comment.query.get(comment_id)
    else:
        comment = None

    if not comment:
        if not user or not post or post.user is not user:
            abort(404)
        item = post
    else:
        if not user or not post or not comment or post.user is not user\
            or comment.post is not post:
            abort(404)
        item = comment

    if item.user != current_user:
        abort(403)

    db.session.delete(item)
    db.session.commit()

    redirect_url = request.values.get('next', None)
    if not redirect_url or not is_safe_url(redirect_url):
        redirect_url=url_for('profile', username=username)

    return redirect(redirect_url)
