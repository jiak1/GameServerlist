from .MCRoutes import MCRoutes
from flask import render_template
from .Program import mc_app as app
import traceback

@MCRoutes.errorhandler(Exception)
def internal_error(error):
	try:
		result = traceback.format_exc()
		with open("logging.txt", "a") as f:
			f.write(result)
	except:
		pass
	return render_template('mc/error.html')
