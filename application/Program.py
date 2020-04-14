from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from elasticsearch import Elasticsearch
import os, base64, re

def getElasticSearchURL():
	bonsai = "https://xSjgyfQXcr:TZeK3dmLUrs7hubkvgx@serverlist-9276239137.ap-southeast-2.bonsaisearch.net:443"
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
	return es_header

###########################
isTesting = True
###########################
#PROJECT_ROOT = "sqlite:///"+os.path.dirname(os.path.realpath(__file__))+"/database/data.db"
PROJECT_ROOT = "mysql://157iUrmRoN:rfGPoXMzty@remotemysql.com/157iUrmRoN"
#PROJECT_ROOT= "mysql://sddusername:sddpassword@db4free.net/sddproject"
#PROJECT_ROOT = "mysql://jiak1_username:Password@johnny.heliohost.org/jiak1_sddprojectdb"

db = SQLAlchemy()
login = LoginManager()
adminLogin = LoginManager()

login.login_view = 'PageRoutes.loginPage'
adminLogin.login_view = "AdminRoutes.homePage"

elasticsearch = Elasticsearch(getElasticSearchURL())


def create_app():
	"""Construct the core application."""
	app = Flask(__name__,static_url_path="", static_folder="static")
	app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
	app.config['SQLALCHEMY_DATABASE_URI'] = PROJECT_ROOT
	app.config['DEBUG']=True
	app.secret_key = 'extra super secret key'

	db.init_app(app)
	login.init_app(app)
	adminLogin.init_app(app)

	with app.app_context():
		# Import
		from .MCRoutes import MCRoutes
		app.register_blueprint(MCRoutes)

		from .AdminRoutes import AdminRoutes
		app.register_blueprint(AdminRoutes)

		from .APIRoutes import APIRoutes
		app.register_blueprint(APIRoutes)

		# Create tables for our models
		db.create_all()

		return app
