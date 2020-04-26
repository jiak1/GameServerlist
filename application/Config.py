import os

IMGDOMAIN=os.getenv("IMG_DOMAIN")
PRODUCTION=bool(os.getenv("PRODUCTION"))

GOOGLE_CLIENT_ID = "608563324926-cc7o80bfiht44qr4joqvrfd6r58sh6n3.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"
SERVER_NAME=os.getenv("SERVER_NAME")

ISADMIN=False
POSTS_PER_PAGE = 6
BONSAIURL=os.getenv("BONSAI_URL")
ADMIN_SECRET=os.getenv("ADMIN_SECRET")
MC_SECRET=os.getenv("MC_SECRET")

DEBUG_MAIL_SETTINGS = {
	"MAIL_SERVER": os.getenv("DEBUG_MAIL_SERVER"),
    "MAIL_PORT": os.getenv("DEBUG_MAIL_PORT"),
    "MAIL_USE_TLS": False,
    "MAIL_USE_SSL": True,
    "MAIL_USERNAME": os.getenv("DEBUG_MAIL_USERNAME"),
    "MAIL_PASSWORD": os.getenv("DEBUG_MAIL_PASSWORD")
}

PRODUCTION_MAIL_SETTINGS = {
	"MAIL_SERVER": os.getenv("PRODUCTION_MAIL_SERVER"),
    "MAIL_PORT": os.getenv("PRODUCTION_MAIL_PORT"),
    "MAIL_USE_TLS": False,
    "MAIL_USE_SSL": True,
    "MAIL_USERNAME": os.getenv("PRODUCTION_MAIL_USERNAME"),
    "MAIL_PASSWORD": os.getenv("PRODUCTION_MAIL_PASSWORD")
}

def SetAdmin(val):
	global ISADMIN
	ISADMIN = val

class AppConfig(object):
	SQLALCHEMY_TRACK_MODIFICATIONS = False
	DEBUG=True
	SQLALCHEMY_POOL_RECYCLE=299
	SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI")
	#SQLALCHEMY_DATABASE_URI= "mysql://serverlistuser:serverlistpass@db4free.net/serverlist"
	RECAPTCHA_PUBLIC_KEY = '6Lep6u0UAAAAAFbBf33eRcCGDUsYygF5uWrTwXVe'
	RECAPTCHA_PRIVATE_KEY = os.getenv("RECAPTCHA_PRIVATE_KEY")
	
GRASSBLOCKICON="data:image/png;base64,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"