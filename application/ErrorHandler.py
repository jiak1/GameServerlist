from .MCRoutes import MCRoutes
from flask import render_template
from sentry_sdk import last_event_id

@MCRoutes.errorhandler(500)
def internal_error(error):
	return render_template('mc/error.html')

@MCRoutes.errorhandler(404)
def not_found_error(error):
	return render_template('mc/error.html')

#@MCRoutes.errorhandler(500)
#def server_error_handler(error):
#    return render_template("mc/error.html", sentry_event_id=last_event_id()), 500