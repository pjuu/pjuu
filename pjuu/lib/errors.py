from flask import jsonify
from pjuu import app, db


@app.errorhandler(404)
def error_404(error):
    return "404", 404


@app.errorhandler(500)
def error_500(error):
    db.session.rollback()
    return "500", 500
