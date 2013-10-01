# 3rd party imports
from flask import (abort, flash, g, redirect, render_template, request,
                   session, url_for)

# Pjuu imports
from pjuu import app, db
from pjuu.auth.backend import current_user
from pjuu.auth.decorators import login_required
from .forms import PostForm
from .models import Post


@app.route('/post', methods=['POST'])
@login_required
def post():
    form = PostForm(request.form)
    redirect_url = request.values.get('next', None)
    if not redirect_url or not is_safe_url(redirect_url):
        redirect_url=url_for('profile', username=current_user.username)
    if form.validate():
        new_post = Post(current_user, form.body.data)
        db.session.add(new_post)
        db.session.commit()
    return redirect(redirect_url)
