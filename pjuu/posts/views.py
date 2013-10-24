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
        try:
            new_post = Post(current_user, form.body.data)
            db.session.add(new_post)
            db.session.commit()
            flash('Posted', 'success')
        except:
            db.session.rollback()
            abort(500)
    else:
        flash('Posts must be between 2 and 512 characters long', 'error')
    return redirect(redirect_url)


@app.route('/<username>/<int:post_id>/comment', methods=['POST'])
@login_required
def comment(username, post_id):
    """
    Should this be in here??? Ah well.
    """
    form = PostForm(request.form)
    # Check that the post_id matches up with that of the user
    user = User.query.filter_by(username=username).first()
    post = Post.query.get(post_id)
    if not user or not post or post.user is not user:
        abort(404)

    if form.validate():
        try:
            new_comment = Comment(current_user, post_id, form.body.data)
            db.session.add(new_comment)
            db.session.commit()
            flash('Comment posted', 'success')
        except:
            db.session.rollback()
            abort(500)
    else:
        flash('Comments must be between 2 and 512 characters long.', 'error')
    return redirect(url_for('view_post', username=username, post_id=post.id))
