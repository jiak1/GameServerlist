from .MCRoutes import MCRoutes
from flask import render_template

@MCRoutes.errorhandler(Exception)
def internal_error(error):
    return render_template('mc/error.html')