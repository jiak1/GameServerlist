from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from sqlalchemy.sql import func;
from .Search import add_to_index, remove_from_index, query_index
from time import time
from .Config import GRASSBLOCKICON
import jwt
from sqlalchemy.inspection import inspect

from .Config import ISADMIN
if(ISADMIN):
	from .Program import admin_db as db,admin_app as app
else:
	from .Program import mc_db as db,mc_app as app

class Serializer(object):

    def serialize(self):
        return {c: getattr(self, c) for c in inspect(self).attrs.keys()}

    @staticmethod
    def serialize_list(l):
        return [m.serialize() for m in l]

class SearchableMixin(object):
    @classmethod
    def search(cls, expression, page, per_page):
        ids, total = query_index(cls.__tablename__, expression, page, per_page)
        if total == 0:
            return cls.query.filter_by(id=0), 0
        when = []
        for i in range(len(ids)):
            when.append((ids[i], i))
        return cls.query.filter(cls.id.in_(ids)).order_by(
            db.case(when, value=cls.id)), total

    @classmethod
    def before_commit(cls, session):
        session._changes = {
            'add': list(session.new),
            'update': list(session.dirty),
            'delete': list(session.deleted)
        }

    @classmethod
    def after_commit(cls, session):
        for obj in session._changes['add']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['update']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['delete']:
            if isinstance(obj, SearchableMixin):
                remove_from_index(obj.__tablename__, obj)
        session._changes = None

    @classmethod
    def reindex(cls):
        for obj in cls.query:
            add_to_index(cls.__tablename__, obj)
db.event.listen(db.session, 'before_commit', SearchableMixin.before_commit)
db.event.listen(db.session, 'after_commit', SearchableMixin.after_commit)

class User(UserMixin,db.Model):
	__abstract__ = True
	id = db.Column(db.Integer, primary_key=True)
	username = db.Column(db.String(100), nullable=False) #Limited to 20 chars
	email = db.Column(db.String(120), nullable=False)
	password_hash = db.Column(db.String(128),nullable=True)

	def set_password(self, password):
		self.password_hash = generate_password_hash(password)

	def check_password(self, password):
		if(self.password_hash != None):
			return check_password_hash(self.password_hash, password)
		else:
			return False

	def get_reset_password_token(self, expires_in=1200):
		return jwt.encode(
            {'reset_password': self.id, 'exp': time() + expires_in},
            app.config['SECRET_KEY'], algorithm='HS256').decode('utf-8')

	def get_email_confirm_token(self, expires_in=9600):
		return jwt.encode(
            {'confirm_email': self.id, 'exp': time() + expires_in},
            app.config['SECRET_KEY'], algorithm='HS256').decode('utf-8')
	
	def get_email_change_token(self):
		return jwt.encode(
            {'change_email': self.id},
            app.config['SECRET_KEY'], algorithm='HS256').decode('utf-8')
			
class Account(User,Serializer):
	accountCreateDate = db.Column(db.DateTime,nullable=False,default=func.now())
	lastDataDownload = db.Column(db.DateTime,nullable=True,default=None)
	isGoogle = db.Column(db.Boolean,default=0,nullable=False)
	emailConfirmed = db.Column(db.Boolean,default=0,nullable=False)
	servers = db.relationship('Server', backref='owner',lazy="dynamic")
	lastEmailConfirmSent = db.Column(db.DateTime,nullable=False,default=func.now())
	passwordChangeSent = db.Column(db.DateTime,nullable=False,default=func.now())
	usernameChangeSent = db.Column(db.DateTime,nullable=False,default=func.now())
	changeEmail = db.Column(db.String(120), nullable=False,default="")
	
	def addServer(self, server):
		if not self.ownsServer(server.id):
			self.servers.append(server)

	def removeServer(self, server):
		if self.ownsServer(server.id):
			self.servers.remove(server)

	def ownsServer(self, serverID):
		return self.servers.filter(id == serverID).count() > 0
	
	@staticmethod
	def verify_reset_password_token(token):
		try:
			id = jwt.decode(token, app.config['SECRET_KEY'],algorithms=['HS256'])['reset_password']
		except:
			return
		return Account.query.get(id)

	@staticmethod
	def verify_email_confirm_token(token):
		try:
			id = jwt.decode(token, app.config['SECRET_KEY'],algorithms=['HS256'])['confirm_email']
		except:
			return
		return Account.query.get(id)

	@staticmethod
	def verify_email_change_token(token):
		try:
			id = jwt.decode(token, app.config['SECRET_KEY'],algorithms=['HS256'])['change_email']
		except:
			return
		return Account.query.get(id)

class Admin(User):
	isOwner = db.Column(db.Boolean,default=0,nullable=False)


class Server(SearchableMixin, db.Model,Serializer):
	__searchable__ = ['name','tags','plugins','datapacks','mods','verified','displayVersion','country','rank','newTime','online']

	id = db.Column(db.Integer, primary_key=True)
	ownerID = db.Column(db.Integer, db.ForeignKey('account.id'))

	votes = db.relationship('Vote', backref='server',lazy="dynamic")

	icon = db.Column(db.Text(),nullable=True,default=GRASSBLOCKICON)
	name = db.Column(db.String(50),index=True,nullable=False)

	courseCreateDate = db.Column(db.DateTime,nullable=False,default=func.now())
	newTime = db.Column(db.DateTime,nullable=True,default=func.now())
	lastPingTime = db.Column(db.DateTime,nullable=True,default=func.now())

	verified = db.Column(db.Integer,default=0,nullable=False)

	ip = db.Column(db.String(35),nullable=False)
	displayIP = db.Column(db.String(60),nullable=True, default="")
	port = db.Column(db.String(5),nullable=False)
	version = db.Column(db.Text(),nullable=True, default="")
	displayVersion = db.Column(db.String(10),nullable=True,default="")
	queryOn = db.Column(db.Boolean,default=0,nullable=False)	

	monthlyVotes = db.Column(db.Integer,default=0,nullable=False)
	totalVotes = db.Column(db.Integer,default=0,nullable=False)
	rank = db.Column(db.Integer,default=10000,nullable=False)
	lastOnlineTime = db.Column(db.DateTime,nullable=False,default=func.now())
	
	online = db.Column(db.Integer,default=1,nullable=False)

	playerCount = db.Column(db.Integer,default=0,nullable=False)
	playerMax = db.Column(db.Integer,default=0,nullable=False)

	country = db.Column(db.String(4),nullable=False)
	description = db.Column(db.Text(),nullable=False)

	serverType = db.Column(db.String(15),nullable=False)

	plugins = db.Column(db.Text(), nullable=True, default="")
	datapacks = db.Column(db.Text(), nullable=True, default="")
	mods = db.Column(db.Text(), nullable=True, default="")

	votifierEnabled = db.Column(db.Boolean,default=0,nullable=False)
	votifierIP = db.Column(db.String(35),nullable=False)
	votifierPort = db.Column(db.String(5),nullable=False)
	votifierToken = db.Column(db.Text(),nullable=True,default="")

	tags = db.Column(db.Text(), nullable=True, default="")

	website = db.Column(db.String(100), nullable=True, default="")
	discord = db.Column(db.String(80), nullable=True, default="")

	trailer = db.Column(db.String(15), nullable=True, default="")

	banner = db.Column(db.Text(), nullable=True, default="/images/main/LoadingBanner.webp?1")

	rejectReason = db.Column(db.Text(), nullable=True, default="")

class ReviewTag(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	tag = db.Column(db.String(50),nullable=False)
	section = db.Column(db.String(15),nullable=False)
	owner = db.Column(db.String(120),nullable=False)

class Vote(db.Model,Serializer):
	id = db.Column(db.Integer, primary_key=True)
	serverID = db.Column(db.Integer, db.ForeignKey('server.id'))

	username = db.Column(db.String(80),nullable=False)
	ip = db.Column(db.String(80),nullable=False)
	voteTime = db.Column(db.DateTime,nullable=False,default=func.now())

class Report(db.Model):
	id = db.Column(db.Integer, primary_key=True)

	serverID = db.Column(db.String(12),nullable=False)
	name = db.Column(db.String(50),nullable=False)

	reason = db.Column(db.String(20),nullable=False)
	description = db.Column(db.Text(),nullable=False)

	reviewed = db.Column(db.Integer,nullable=False,default=0)