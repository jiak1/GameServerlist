from flask import request, render_template,Blueprint,redirect,flash,url_for,send_from_directory, jsonify,abort
from .Program import db,login,isTesting
from flask_login import current_user, login_user,logout_user, login_required
import os
from .Forms import LoginForm,RegisterForm,ServerForm
from .Models import Account, Server
from .Util import UpdateServerWithForm

MCRoutes = Blueprint('MCRoutes', __name__)
curDir = os.path.dirname(os.path.realpath(__file__))
from .Program import elasticsearch

#elasticsearch.indices.create(index='server')
#Server.reindex()

prefix = "/"
if(isTesting):
	prefix = "/minecraft/" 

@MCRoutes.route("/",methods=['GET'])
def headerPage():
	return render_template("index.html")

@MCRoutes.route(prefix,methods=['GET','POST'])
def MCHomePage():
	if(request.method == "POST"):
		query = request.form['search']
		servers, total = Server.search(query,1,10)
		return render_template("mc/index.html",servers=servers)
	else:
		servers = Server.query.filter_by(verified=1)
		return render_template("mc/index.html",servers=servers)

@MCRoutes.route(prefix+"login",methods=['GET', 'POST'])
def loginPage():
	if current_user.is_authenticated:
		 return redirect(url_for('MCRoutes.MCHomePage'))
	form = LoginForm()
	if form.validate_on_submit():
		user = Account.query.filter_by(username=form.username.data).first()
		if user is None or not user.check_password(form.password.data):
			flash('Invalid username or password',"danger")
			return redirect(url_for('MCRoutes.loginPage'))
		login_user(user, remember=form.remember_me.data)
		return redirect(url_for('MCRoutes.MCHomePage'))
	return render_template('mc/login.html', form=form)

@MCRoutes.route(prefix+"register", methods=['GET', 'POST'])
def registerPage():
	if current_user.is_authenticated:
		return redirect(url_for('MCRoutes.loginPage'))
	form = RegisterForm()
	if form.validate_on_submit():
		user = Account(username=form.username.data, email=form.email.data)
		user.set_password(form.password.data)
		db.session.add(user)
		db.session.commit()
		flash('Congratulations, your account has been created!',"success")
		return redirect(url_for('MCRoutes.MCHomePage'))
	else:
		for key in form.errors:
			flash(form.errors[key][0],"danger")
	return render_template('mc/register.html', form=form)

@MCRoutes.route(prefix+"logout",methods=['GET'])
def logoutPage():
	logout_user()
	return redirect(url_for('MCRoutes.MCHomePage'))

@login.user_loader
def load_account(id):
	return Account.query.get(int(id))

@MCRoutes.route(prefix+"advertise",methods=['GET'])
def advertisePage():
	if not current_user.is_authenticated:
		return render_template("mc/notallowed.html")

@MCRoutes.route(prefix+"addserver",methods=['GET','POST'])
def addServerPage():
	if not current_user.is_authenticated:
		return render_template("mc/notallowed.html")
	form = ServerForm()
	if form.validate_on_submit():
		user = Account.query.filter_by(id=current_user.id).first()
		if(user is not None and user.id == current_user.id):
			server = Server(owner=user,verified=0)
			UpdateServerWithForm(form,server)
			db.session.add(server)
			db.session.commit()

			flash('Your server has been submitted for review!',"success")
			redirect(url_for('MCRoutes.MCHomePage'))
		else:
			flash("Invalid session, please log in again.","danger")
	else:
		for key in form.errors:
			flash(form.errors[key][0],"danger")
	return render_template("mc/editServer.html", form=form, create=True, edit=False, header="Add Your Server")

@login_required
@MCRoutes.route(prefix+"servers",methods=['GET'])
def serversPage():
	return render_template("mc/base.html")

@MCRoutes.route(prefix+"server",methods=['GET'])
def serverInfoPage():
	return "Works"