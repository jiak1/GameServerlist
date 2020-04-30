from .MCRoutes import MCRoutes
from flask import render_template
import traceback

@MCRoutes.errorhandler(500)
def internal_error(error):
	try:
		result = traceback.format_exc()
		with open("logging.txt", "a") as f:
			f.write(result)
	except:
		pass
	return render_template('mc/error.html')

@MCRoutes.errorhandler(404)
def not_found_error(error):
	try:
		result = traceback.format_exc()
		with open("logging.txt", "a") as f:
			f.write(result)
	except:
		pass
	return render_template('mc/error.html')