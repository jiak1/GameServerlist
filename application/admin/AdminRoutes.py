from flask import request, render_template,Blueprint,redirect,flash,url_for,send_from_directory, jsonify,abort
from ..Program import admin_db as db,admin_login as login,elasticsearch
from flask_login import current_user, login_user,logout_user, login_required
import os
from ..Forms import LoginForm,RegisterForm,AdminServerForm,PasswordChangeForm,EmailChangeForm,TagsForm,ViewTagsForm
from ..Models import Admin,Server,Account,ReviewTag,Report
from ..Util import UpdateAdminServerWithForm,addNewTags,sendServerApprovedEmail,sendServerDeniedEmail,serverRank,logServerGraphs,checkServerUpdates,transitionVotesMonth, sendServerNotifyEmail,getTagData,forceUpdateTagSection
from ..Config import getProduction,INDEX_CREATION
import datetime

AdminRoutes = Blueprint('AdminRoutes', __name__)
curDir = os.path.dirname(os.path.realpath(__file__))

prefix = "/"
if(getProduction() == False):
	prefix = "/admin/"

@login.user_loader
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

@AdminRoutes.route(prefix+"reviews",methods=['GET'])
@login_required
def reviewsPage():
	reviews = Server.query.filter_by(verified=0).order_by(Server.id).paginate(1,20,False).items
	reports = Report.query.filter_by(reviewed=0).order_by(Report.serverID).paginate(1,20,False).items
	reReviewed = Server.query.filter_by(verified=3).order_by(Server.id).paginate(1,20,False).items
	for item in reReviewed:
		reviews.append(item)
	tags = ReviewTag.query.first()
	needToReviewTags = True
	if(tags is None):
		needToReviewTags = False

	return render_template("admin/reviews.html",reviews=reviews,needToReviewTags=needToReviewTags,reports=reports)

@AdminRoutes.route(prefix+"report",methods=['GET'])
@login_required
def reportPage():
	report = Report.query.get(int(request.args.get("id")))
	if(report is None):
		return redirect(url_for("AdminRoutes.reviewsPage"))
	action = request.args.get("action")
	if(action is not None):
		action = request.args['action']
		if(action == "allow"):
			flash("Removed False Report","primary")
			db.session.delete(report)
		elif(action == "deny"):
			flash("Report Marked As Reviewed","success")
			report.reviewed = 1
		db.session.commit()
		return redirect(url_for("AdminRoutes.reviewsPage"))
	for item in request.args:
		print(request.args[item])
	return render_template("admin/report.html",report=report)

@AdminRoutes.route(prefix+"profile",methods=['GET','POST'])
@login_required
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

@AdminRoutes.route(prefix+"review",methods=['GET','POST'])
@login_required
def reviewPage():
	serverID = request.args.get('id')
	server = Server.query.filter_by(id=serverID).first()
	form = AdminServerForm();
	if('action' in request.args):
		if(request.args.get('action') == "APPROVE"):
			UpdateAdminServerWithForm(form,server)
			server.verified = 1
			db.session.commit();
			flash('Successfully approved server.','success')
			sendServerApprovedEmail(server)
			return redirect(url_for("AdminRoutes.reviewsPage"))	
		elif(request.args.get('action') == "REJECT"):
			UpdateAdminServerWithForm(form,server)
			server.verified = 2
			db.session.commit();
			flash('Successfully rejected server.','warning')
			sendServerDeniedEmail(server)
			return redirect(url_for("AdminRoutes.reviewsPage"))	
		elif(request.args.get('action') == "UPDATE"):
			UpdateAdminServerWithForm(form,server)
			db.session.commit()
			flash('Successfully updated case.','primary')
			return redirect(url_for("AdminRoutes.reviewPage")+"?id="+serverID)
		elif(request.args.get('action') == "BAN"):
			UpdateAdminServerWithForm(form,server)
			server.verified = 10
			db.session.commit()
			flash('Successfully banned server.','warning')
			return redirect(url_for("AdminRoutes.reviewPage")+"?id="+serverID)
		elif(request.args.get('action') == "EMAIL"):
			UpdateAdminServerWithForm(form,server)
			db.session.commit()
			sendServerNotifyEmail(server)
			flash('Successfully sent email.','success')
			return redirect(url_for("AdminRoutes.reviewPage")+"?id="+serverID)
	if(server is not None):
		return render_template("admin/review.html",server=server,form=form)
	else:
		return redirect(url_for("AdminRoutes.reviewsPage"))

@AdminRoutes.route(prefix+"reviewtags",methods=['GET','POST'])
@login_required
def reviewTagsPage():
	form = TagsForm()
	tags = ReviewTag.query.all()
	return render_template("admin/reviewTags.html",form=form,tags=tags)

@AdminRoutes.route(prefix+"tagsView",methods=['GET','POST'])
@login_required
def tagsViewPage():
	form = ViewTagsForm()
	if(request.method == "POST"):
		try:
			forceUpdateTagSection("mods",form.mods.data)
			forceUpdateTagSection("datapacks",form.datapacks.data)
			forceUpdateTagSection("plugins",form.plugins.data)
			forceUpdateTagSection("tags",form.tags.data)
		except:
			flash("Incorrect JSON Syntax","danger")

		return redirect(url_for("AdminRoutes.tagsViewPage"))
	else:
		mods = getTagData("mods")
		datapacks = getTagData("datapacks")
		plugins = getTagData("plugins")
		tags = getTagData("tags")

		return render_template("admin/viewTags.html",form=form, mods=mods,datapacks=datapacks,plugins=plugins,tags=tags)

@AdminRoutes.route("/admin/API/REMOVEREVIEW",methods=['GET'])
@login_required
def APIRemoveReview():
	id = request.args.get("ID")
	_tag = ReviewTag.query.filter_by(id=id).first()
	if(_tag is not None):
		db.session.delete(_tag)
		db.session.commit()
		return jsonify(success=True)
	abort(400)

@AdminRoutes.route("/admin/API/ADDTAGS",methods=['POST'])
@login_required
def APIAddTags():
	data = request.get_json();
	tags = data['TAGS']
	mods = data['MODS']
	datapacks = data['DATAPACKS']
	plugins = data['PLUGINS']
	addNewTags(tags,mods,plugins,datapacks)
	return jsonify(success=True)

@AdminRoutes.route(prefix+"elasticsearch",methods=['GET'])
@login_required
def esSetupPage():
	elasticsearch.indices.create(index='server',body=INDEX_CREATION)
	return redirect(url_for("AdminRoutes.homePage"))

@AdminRoutes.route(prefix+"esdelete",methods=['GET'])
@login_required
def esDeletePage():
	elasticsearch.indices.delete(index='server', ignore=[400, 404])
	return redirect(url_for("AdminRoutes.homePage"))

#Elasticsearch update!
@AdminRoutes.route(prefix+"reindex",methods=['GET'])
@login_required
def esReindexPage():
	Server.reindex()
	return redirect(url_for("AdminRoutes.homePage"))

@AdminRoutes.route(prefix+"rank",methods=['GET'])
@login_required
def rankPage():
	serverRank()
	return redirect(url_for("AdminRoutes.homePage"))

@AdminRoutes.route(prefix+"graph",methods=['GET'])
def APIGRAPH():
	logServerGraphs()
	return redirect(url_for("AdminRoutes.homePage"))

@AdminRoutes.route(prefix+"pingservers",methods=['GET'])
def APIPING():
	checkServerUpdates()
	return redirect(url_for("AdminRoutes.homePage"))

@AdminRoutes.route(prefix+"newmonth",methods=['GET'])
@login_required
def voteMonthChange():
	transitionVotesMonth()
	return redirect(url_for("AdminRoutes.homePage"))

@AdminRoutes.route(prefix+"break",methods=['GET'])
def breakPage():
	print(1+"2")
	return "test"
