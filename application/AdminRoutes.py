from flask import request, render_template,Blueprint,redirect,flash,url_for,send_from_directory, jsonify,abort
from .Program import db,adminLogin,isTesting
from flask_login import current_user, login_user,logout_user, login_required
import os
from .Forms import LoginForm,RegisterForm,ServerForm,PasswordChangeForm,EmailChangeForm
from .Models import Account, Server,Admin
from .Util import UpdateServerWithForm

AdminRoutes = Blueprint('AdminRoutes', __name__)
curDir = os.path.dirname(os.path.realpath(__file__))

prefix = "/"
if(isTesting):
	prefix = "/admin/"

@adminLogin.user_loader
def load_account(id):
	return Admin.query.get(int(id))

@AdminRoutes.route(prefix,methods=['GET','POST'])
def homePage():
	if current_user.is_authenticated:
		 return redirect(url_for('AdminRoutes.profilePage'))
	form = LoginForm()
	if form.validate_on_submit():
		user = Admin.query.filter_by(username=form.username.data).first()
		if user is None or not user.check_password(form.password.data):
			flash('Invalid username or password',"danger")
			return redirect(url_for('AdminRoutes.homePage'))
		login_user(user, remember=form.remember_me.data)
		return redirect(url_for('AdminRoutes.profilePage'))
	else:
		for key in form.errors:
			flash(form.errors[key][0],"danger")
	return render_template("admin/index.html",form=form)

@login_required
@AdminRoutes.route(prefix+"reviews",methods=['GET'])
def reviewsPage():
	reviews = Server.query.filter_by(verified=0).order_by(Server.id).paginate(1,20,False).items
	return render_template("admin/reviews.html",reviews=reviews)

@login_required
@AdminRoutes.route(prefix+"profile",methods=['GET','POST'])
def profilePage():
	form = PasswordChangeForm()
	if form.validate_on_submit():
		user = Admin.query.filter_by(id=current_user.id).first()
		user.set_password(form.newPassword.data)
		db.session.commit();
		flash('Changed password.',"success")
		return redirect(url_for('AdminRoutes.profilePage'))
	elif(form.passwordSubmit.data):
		for key in form.errors:
			flash(form.errors[key][0],"danger")

	emailForm = EmailChangeForm()
	if emailForm.validate_on_submit():
		user = Admin.query.filter_by(id=current_user.id).first()
		user.email = emailForm.newEmail.data
		db.session.commit();
		flash('Changed email.',"success")
		return redirect(url_for('AdminRoutes.profilePage'))
	elif(emailForm.emailSubmit.data):
		for key in emailForm.errors:
			flash(emailForm.errors[key][0],"danger")

	adduser = RegisterForm();
	if adduser.validate_on_submit():
		exists = Admin.query.filter_by(username=adduser.username.data).first()
		if(exists is None and current_user.isOwner):
			admin = Admin(username=adduser.username.data, email=adduser.email.data)
			admin.set_password(adduser.password.data)
			db.session.add(admin)
			db.session.commit()
			flash('Added new Administrator account.',"success")
		else:
			flash("An account with that username already exists","danger")
	elif adduser.submit.data:
		for key in adduser.errors:
			flash(adduser.errors[key][0],"danger")
	return render_template("admin/profile.html",form=form,adduserform=adduser,emailForm=emailForm)

@AdminRoutes.route(prefix+"logout",methods=['GET'])
def logoutPage():
	logout_user()
	return redirect(url_for("AdminRoutes.homePage"))

@login_required
@AdminRoutes.route(prefix+"review",methods=['GET','POST'])
def reviewPage():
	serverID = request.args.get('id')
	server = Server.query.filter_by(id=serverID).first()
	form = ServerForm();
	if('action' in request.args):
		if(request.args.get('action') == "APPROVE"):
			UpdateServerWithForm(form,server)
			server.verified = 1
			server.rejectReason = form.rejectReason.data
			db.session.commit();
			flash('Successfully approved server.','success')
			redirect("AdminRoutes.reviewsPage")	
		else:
			UpdateServerWithForm(form,server)
			server.verified = 2
			server.rejectReason = form.rejectReason.data
			db.session.commit();
			flash('Successfully rejected server.','warning')
			redirect("AdminRoutes.reviewsPage")	
	if(server is not None and server.verified==0):
		return render_template("admin/review.html",server=server,form=form)
	else:
		return redirect(url_for("AdminRoutes.reviewsPage"))