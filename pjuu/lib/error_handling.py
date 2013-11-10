from flask import jsonify
from pjuu import app


@app.errorhandler(404)
def error_404(error):
    return "404", 404


@app.errorhandler(500)
def error_500(error):
    return "500", 500
