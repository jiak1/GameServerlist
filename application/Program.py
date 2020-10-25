from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from elasticsearch import Elasticsearch,RequestsHttpConnection
from flask_mail import Mail
from flask_crontab import Crontab
from flask_migrate import Migrate
import re
from .Config import *
from oauthlib.oauth2 import WebApplicationClient
from .momentjs import momentjs
from requests_aws4auth import AWS4Auth
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
#from sentry_sdk.integrations.aiohttp import AioHttpIntegration

def getElasticSearchURL():
	if(getProduction() == True):
		host = BONSAIURL # WITHOUT HTTP AND ENDING /
		region = 'us-east-2' # e.g. us-east-2

		service = 'es'

		awsauth = AWS4Auth(CREDENTIALS_ACCESS_KEY, CREDENTIALS_SECRET_KEY, region, service)

		return Elasticsearch(
			hosts = [{'host': host, 'port': 443}],
			http_auth = awsauth,
			use_ssl = True,
			verify_certs = True,
			connection_class = RequestsHttpConnection, timeout=10, max_retries=3, retry_on_timeout=True
		)
	bonsai = BONSAIURL
	auth = re.search('https\:\/\/(.*)\@', bonsai).group(1).split(':')
	host = bonsai.replace('https://%s:%s@' % (auth[0], auth[1]), '')

	# optional port
	match = re.search('(:\d+)', host)
	if match:
		p = match.group(0)
		host = host.replace(p, '')
		port = int(p.split(':')[1])
	else:
		port=443

	# Connect to cluster over SSL using auth for best security:
	es_header = [{
	'host': host,
	'port': port,
	'use_ssl': True,
	'http_auth': (auth[0],auth[1])
	}]
	return Elasticsearch(es_header, timeout=10, max_retries=3, retry_on_timeout=True)


#PROJECT_ROOT = "sqlite:///"+os.path.dirname(os.path.realpath(__file__))+"/database/data.db"
#PROJECT_ROOT= "mysql://sddusername:sddpassword@c/sddproject"
#PROJECT_ROOT = "mysql://jiak1_username:Password@johnny.heliohost.org/jiak1_sddprojectdb"

elasticsearch = getElasticSearchURL()

mc_db = SQLAlchemy()
admin_db = SQLAlchemy()

mc_login = LoginManager()
admin_login = LoginManager()

mc_mail = Mail();
admin_mail = Mail();

mc_crontab = Crontab()
admin_crontab = Crontab()

migrate = Migrate()

client = WebApplicationClient(GOOGLE_CLIENT_ID)

mc_login.login_view = 'MCRoutes.loginPage'
admin_login.login_view = "AdminRoutes.homePage"
if(getProduction() == True):
	mail_settings = PRODUCTION_MAIL_SETTINGS
else:
	mail_settings = DEBUG_MAIL_SETTINGS

def create_mc_app():
	sentry_sdk.init("https://48bd4af68237433c8b42f566835b585d@o385754.ingest.sentry.io/5226663",integrations=[FlaskIntegration(),SqlalchemyIntegration()])
	"""Construct the core mc_application."""
	global mc_app
	mc_app = Flask(__name__,static_url_path="", static_folder="static")

	mc_app.config.from_object(AppConfig)
	
	mc_app.config.update(mail_settings)
	mc_app.config['ADMINS']= ['jackdonaldson005@gmail.com']
	if(getProduction() == True):
		mc_app.config['SERVER_NAME']= "minecraft.server-lists.com"

	mc_app.secret_key = MC_SECRET

	mc_db.init_app(mc_app)
	mc_login.init_app(mc_app)

	mc_crontab.init_app(mc_app)
	migrate.init_app(mc_app)

	mc_app.jinja_env.globals['momentjs'] = momentjs
	
	mc_mail.init_app(mc_app)
	from .Setup import setup
	setup(mc_app)

	#if(PRODUCTION):
	#	mc_app.config['SERVER_NAME']="minecraft.server-lists.com"
	#else:
	#	mc_app.config['SERVER_NAME']="serverlist.jackdonaldson1.repl.co"	

	with mc_app.app_context():
		# Import
		from .MCRoutes import MCRoutes
		mc_app.register_blueprint(MCRoutes)

		from .APIRoutes import APIRoutes
		mc_app.register_blueprint(APIRoutes)

		# Create tables for our models
		mc_db.create_all()

		return mc_app

def create_admin_app():
	sentry_sdk.init("https://48bd4af68237433c8b42f566835b585d@o385754.ingest.sentry.io/5226663",integrations=[FlaskIntegration(),SqlalchemyIntegration()])
	"""Construct the core admin_application."""
	global admin_app
	admin_app = Flask(__name__,static_url_path="", static_folder="static")
	admin_app.config.from_object(AppConfig)

	admin_app.config.update(mail_settings)
	admin_app.config['ADMINS']= ['jackdonaldson005@gmail.com']
	if(getProduction()):
		admin_app.config['SERVER_NAME']= "admin.server-lists.com"

	admin_app.secret_key = ADMIN_SECRET

	admin_db.init_app(admin_app)
	admin_login.init_app(admin_app)

	admin_crontab.init_app(admin_app)

	admin_mail.init_app(admin_app)
	from .Setup import setup
	setup(admin_app)

	#if(PRODUCTION):
	#	admin_app.config['SERVER_NAME']="admin.server-lists.com"
	#else:
	#	admin_app.config['SERVER_NAME']="serverlist.jackdonaldson1.repl.co"	

	with admin_app.app_context():
		# Import
		from .admin.AdminRoutes import AdminRoutes
		admin_app.register_blueprint(AdminRoutes)

		# Create tables for our models
		admin_db.create_all()

		return admin_app