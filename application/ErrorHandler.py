from .MCRoutes import MCRoutes
from flask import render_template
from .Program import mc_app as app

@MCRoutes.errorhandler(500)
def internal_error(error):
	return render_template('mc/error.html'),500

@MCRoutes.errorhandler(404)
def not_found_error(error):
	return render_template('mc/error.html'),404