import logging
from logging.handlers import SMTPHandler
from .Config import getProduction
def setup(app):
	if(getProduction() == False):
		return
	mail_handler = SMTPHandler(
				mailhost=(app.config['MAIL_SERVER'], 587),
				fromaddr='jackdonaldson005@gmail.com',
				toaddrs=app.config['ADMINS'], subject='Serverlist Failure',
				credentials=(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD']), secure=())
	mail_handler.setLevel(logging.ERROR)
	app.logger.addHandler(mail_handler)