# 3rd party imports
from flask import (abort, flash, g, redirect, render_template, request,
                   session, url_for)

# Pjuu imports
from pjuu import app, db
from pjuu.auth.backend import current_user
from pjuu.auth.decorators import login_required
from pjuu.users.models import User
from .forms import PostForm
from .models import Comment, Post


@app.route('/post', methods=['POST'])
@login_required
def post():
    form = PostForm(request.form)
    if form.validate():
        try:
            new_post = Post(current_user, form.body.data)
            db.session.add(new_post)
            db.session.commit()
        except:
            abort(500)
    return redirect(url_for('profile', username=current_user.username))


@app.route('/<username>/<int:post_id>/comment', methods=['POST'])
@login_required
def comment(username, post_id):
    form = PostForm(request.form)
    # Check that the post_id matches up with that of the user
    user = User.query.filter_by(username=username)
    post = Post.query.get(post_id)
    if not user or not post or not post.user is user:
        abort(404)
    if form.validate():
        try:
            new_comment = Comment(current_user, post_id, form.body.data)
            db.session.add(new_post)
            db.session.commit()
        except:
            abort(500)
    return redirect(url_for('view_post', username=user.usename, post_id=post.id))
