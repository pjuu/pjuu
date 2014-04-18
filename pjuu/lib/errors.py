# -*- coding: utf8 -*-
# 3rd party imports
from flask import render_template
# Pjuu imports
from pjuu import app


__all__ = ['page_not_found', 'forbidden', 'internal_server_error']


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(403)
def forbidden(e):
    return render_template('403.html'), 403


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500