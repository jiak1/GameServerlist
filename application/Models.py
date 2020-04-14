from .Program import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from sqlalchemy.sql import func;
from .Search import add_to_index, remove_from_index, query_index

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

class User(UserMixin, db.Model):
	__abstract__=True
	id = db.Column(db.Integer, primary_key=True)
	username = db.Column(db.String(20), nullable=False) #Limited to 20 chars
	email = db.Column(db.String(120), nullable=False)
	password_hash = db.Column(db.String(128),nullable=False)
	
	def set_password(self, password):
		self.password_hash = generate_password_hash(password)

	def check_password(self, password):
		return check_password_hash(self.password_hash, password)

	def __repr__(self):
		return (f"Created {self.username}'s account")


class Account(User):
	accountCreateDate = db.Column(db.DateTime,nullable=False,default=func.now())

	servers = db.relationship('Server', backref='owner',lazy="dynamic")

	def addServer(self, server):
		if not self.ownsServer(server.id):
			self.servers.append(server)

	def removeServer(self, server):
		if self.ownsServer(server.id):
			self.servers.remove(server)

	def ownsServer(self, serverID):
		return self.servers.filter(id == serverID).count() > 0

class Admin(User):
	isOwner = db.Column(db.Boolean,default=0,nullable=False)


class Server(SearchableMixin, db.Model):
	__searchable__ = ['name','tags','plugins','datapacks','mods','verified','version']

	id = db.Column(db.Integer, primary_key=True)
	ownerID = db.Column(db.Integer, db.ForeignKey('account.id'))

	name = db.Column(db.String(50),index=True,nullable=False)

	courseCreateDate = db.Column(db.DateTime,nullable=False,default=func.now())

	verified = db.Column(db.Integer,default=0,nullable=False)

	ip = db.Column(db.String(35),nullable=False)
	port = db.Column(db.String(5),nullable=False)
	version = db.Column(db.String(8),nullable=True, default="")
	votes = db.Column(db.Integer,default=0,nullable=False)
	rank = db.Column(db.Integer,default=0,nullable=False)

	country = db.Column(db.String(4),nullable=False)
	description = db.Column(db.Text(),nullable=False)

	serverType = db.Column(db.String(15),nullable=False)

	plugins = db.Column(db.Text(), nullable=True, default="")
	datapacks = db.Column(db.Text(), nullable=True, default="")
	mods = db.Column(db.Text(), nullable=True, default="")

	tags = db.Column(db.Text(), nullable=True, default="")

	website = db.Column(db.String(100), nullable=True, default="")
	discord = db.Column(db.String(15), nullable=True, default="")

	trailer = db.Column(db.String(15), nullable=True, default="")

	banner = db.Column(db.Text(), nullable=True, default="")

	rejectReason = db.Column(db.Text(), nullable=True, default="")

	def __repr__(self):
		return "Created new course!"