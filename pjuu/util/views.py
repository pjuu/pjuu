# -*- coding: utf8 -*-

# Stdlib imports
from time import gmtime
from calendar import timegm
# 3rd party imports
from flask import render_template, jsonify
# Pjuu imports
from pjuu import (app, redis as r, __version__)


@app.context_processor
def inject_version():
    """
    Injects Pjuu __version__ into the Jinja environment
    """
    return dict(version=__version__)


@app.route('/stats', methods=['GET'])
def statistics():
    """
    Will display Pjuu statistics. Users, Posts, Comments etc...
    This returns as JSON for future plugin to Robotter
    """
    stats = {
        'time': timegm(gmtime()),
        'version': __version__,
        'user_count': len(r.keys('user:*')),
        'post_count': len(r.keys('post:*')),
        'comment_count': len(r.keys('comment:*')),
    }
    return jsonify(stats)