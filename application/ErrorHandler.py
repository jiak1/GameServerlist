from .MCRoutes import MCRoutes
from flask import render_template
from .Program import mc_app as app
import traceback #NEEDED FOR FORMAT_EXC
app.logger.info("SETTING UP LOGGER")

@MCRoutes.errorhandler(Exception)
def internal_error(error):
	result = error.format_exc()
	app.logger.info(result)
	return render_template('mc/error.html')