from flask import request, render_template,Blueprint,redirect,flash,url_for,send_file
from .Program import mc_db as db,mc_login as login,client
from flask_login import current_user, login_user,logout_user, login_required
import os
from .Forms import LoginForm,RegisterForm,ServerForm,ResetPasswordForm,VotifierTestForm,AccountEmailChangeForm,AccountPasswordChangeForm,VoteForm,AccountUsernameChangeForm,AccountGoogleLinkForm,AccountDeleteForm,ServerDeleteForm
from .Models import Account, Server,Vote
from .Util import UpdateServerWithForm,update_server_details, send_password_reset_email,send_username_reminder_email, getVersion,get_google_provider_cfg,sendVotifierVote,validateServer,sendData,updateTagRequests,verifyCaptcha,checkHasVoted,submitVote,sendConfirmEmail
from .Config import PRODUCTION,GOOGLE_CLIENT_ID,GOOGLE_CLIENT_SECRET,POSTS_PER_PAGE
import requests
import json
import datetime
from PIL import Image,ImageSequence

MCRoutes = Blueprint('MCRoutes', __name__)
curDir = os.path.dirname(os.path.realpath(__file__))
APP_ROOT = os.path.dirname(os.path.abspath(__file__))

prefix = "/"
if(PRODUCTION == False):
	prefix = "/minecraft/" 
	print("A")

@MCRoutes.route(prefix,methods=['GET'])
def MCHomePage():
	page = request.args.get('page', 1, type=int)
	search = request.args.get('search', "")
	try:
		servers,total = Server.search(search,page,POSTS_PER_PAGE)
		if total > page * POSTS_PER_PAGE:
			next_url = url_for('MCRoutes.MCHomePage', search=search, page=page + 1)
		else:
			next_url=None
		if page > 1:
			prev_url = url_for('MCRoutes.MCHomePage', search=search, page=page - 1)
		else:
			prev_url=None
		return render_template("mc/index.html",servers=servers,search=search,next_url=next_url,prev_url=prev_url)
	except:
		#runs if we go to an invalid page
		return redirect(url_for("MCRoutes.MCHomePage",search=search))
 

@MCRoutes.route(prefix+"tag/<tagname>",methods=['GET'])
def tagSearchPage(tagname):
	try:
		page = request.args.get('page', 1, type=int)
		search = tagname
		servers,total = Server.search(search,page,POSTS_PER_PAGE)
		if total > page * POSTS_PER_PAGE:
			next_url = url_for('MCRoutes.tagSearchPage',tagname=tagname, page=page + 1)
		else:
			next_url=None
		if page > 1:
			prev_url = url_for('MCRoutes.tagSearchPage',tagname=tagname, page=page - 1)
		else:
			prev_url=None
		return render_template("mc/index.html",servers=servers,search=search,next_url=next_url,prev_url=prev_url)
	except:
		#runs if we go to an invalid page
		return redirect(url_for("MCRoutes.tagSearchPage",search=tagname))

@MCRoutes.route(prefix+"tags",methods=['GET'])
def tagsPage():
	return render_template("mc/tags.html",search="")	

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
		if(user.emailConfirmed == 0):
			return redirect(url_for("MCRoutes.emailConfirmationPage"))
		login_user(user, remember=form.remember_me.data)
		return redirect(url_for('MCRoutes.MCHomePage'))
	return render_template('mc/login.html', form=form)

loginURL = request.base_url
if(PRODUCTION):
	loginURL = "minecraft.server-lists.com/googlelogin/callback"

@MCRoutes.route(prefix+"googlelogin",methods=['GET'])
def googleLoginPage():
	google_provider_cfg = get_google_provider_cfg()
	authorization_endpoint = google_provider_cfg["authorization_endpoint"]
    
    # Use library to construct the request for Google login and provide
    # scopes that let you retrieve user's profile from Google
	request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri=loginURL,
        scope=["openid", "email", "profile"],
		prompt="select_account"
    )
	return redirect(request_uri)

@MCRoutes.route(prefix+"register", methods=['GET', 'POST'])
def registerPage():
	if current_user.is_authenticated:
		return redirect(url_for('MCRoutes.MCHomePage'))
	form = RegisterForm()
	if form.validate_on_submit():
		user = Account(username=form.username.data, email=form.email.data)
		user.set_password(form.password.data)
		user.emailConfirmed = 0
		db.session.add(user)
		db.session.commit()
		sendConfirmEmail(user)
		flash("An email has been sent to activate your account.","success")
		return redirect(url_for('MCRoutes.loginPage'))
	else:
		for key in form.errors:
			flash(form.errors[key][0],"danger")
	return render_template('mc/register.html', form=form)

@MCRoutes.route(prefix+"emailConfirmation", methods=['GET','POST'])
def emailConfirmationPage():
	if(request.method == "POST"):
		if('email' in request.form and request.form['email'] != ""):
			getUser = Account.query.filter_by(email=request.form['email']).first()
			if(getUser is not None):
				if(getUser.emailConfirmed == 0):
					if(getUser.lastEmailConfirmSent < datetime.datetime.now()-datetime.timedelta(minutes=1)):
						sendConfirmEmail(getUser)
						getUser.lastEmailConfirmSent = datetime.datetime.now()
						db.session.commit()
						flash("Successfully sent Account Activation Email.","success")
					else:
						flash("An activation email has been sent within the past minute. Please be patient and check your spam and junk inboxes.","warning")
				else:
					flash("The Account for that email address is already activated.","warning")
			else:
				flash("There is not an account linked to that email address.","danger")
		else:
			flash("Please enter a valid email address.","danger")
	return render_template("mc/emailconfirm.html")

@MCRoutes.route(prefix+"confirmEmail/<token>", methods=['GET'])
def confirmEmailPage(token):
	if current_user.is_authenticated:
		return redirect(url_for('MCRoutes.MCHomePage'))
	user = Account.verify_email_confirm_token(token)
	if not user:
		flash("Invalid email token. Did you wait more then 30 minutes?","danger")
		return redirect(url_for('MCRoutes.emailConfirmationPage'))
	user.emailConfirmed = 1
	db.session.commit()
	flash('Your account has been activated. You may now log in.',"success")
	return redirect(url_for('MCRoutes.loginPage'))

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

@login_required
@MCRoutes.route(prefix+"servers",methods=['GET'])
def serversPage():
	servers = current_user.servers
	if(servers.count() == 0):
		return redirect(url_for("MCRoutes.addServerPage"))
	return render_template("mc/myServers.html", servers=servers)

@MCRoutes.route(prefix+"server",methods=['GET'])
def serverInfoPage():
	return "Works"

@MCRoutes.errorhandler(404)
def not_found_error(error):
    return render_template('mc/error.html'), 404

@MCRoutes.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('mc/error.html'), 500

@MCRoutes.route(prefix+"forgotpassword",methods=['GET','POST'])
def forgotPasswordPage():
	if current_user.is_authenticated:
		return redirect(url_for('MCRoutes.MCHomePage'))
	if(request.method == "POST"):
		email = request.form['email']
		account = Account.query.filter_by(email=email).first()
		if account:
			if(account.isGoogle):
				flash("This email is linked to a google account, the only way to change the password is through Google. We do not have your password.","primary")
			else:
				flash('Check your email for the instructions to reset your password.',"success")
				send_password_reset_email(account)
		else:
			flash('This email is not linked to an account.',"danger")
	return render_template("mc/forgotpassword.html")

@MCRoutes.route(prefix+"forgotusername",methods=['GET','POST'])
def forgotUsernamePage():
	if current_user.is_authenticated:
		return redirect(url_for('MCRoutes.MCHomePage'))
	if(request.method == "POST"):
		email = request.form['email']
		account = Account.query.filter_by(email=email).first()
		if account:
			if(account.isGoogle):
				flash("This email is linked to a google account, simply choose the login with Google option when trying to sign in. You do not require a username.","primary")
			else:
				send_username_reminder_email(account)
				flash('Check your email for your username.',"success")
		else:
			flash('This email is not linked to an account.',"danger")
	return render_template("mc/forgotusername.html")

@MCRoutes.route(prefix+'resetpassword/<token>', methods=['GET', 'POST'])
def resetPasswordPage(token):
	if current_user.is_authenticated:
		return redirect(url_for('MCRoutes.MCHomePage'))
	user = Account.verify_reset_password_token(token)
	if not user:
		flash("Invalid password reset token. Did you wait more then 10 minutes?","danger")
		return redirect(url_for('MCRoutes.forgotPasswordPage'))
	form = ResetPasswordForm()
	if form.validate_on_submit():
		user.set_password(form.password.data)
		db.session.commit()

		flash('Your password has been reset.',"success")
		return redirect(url_for('MCRoutes.loginPage'))
	return render_template("mc/resetpassword.html",form=form)

@MCRoutes.route(prefix+"votifiertest",methods=['GET','POST'])
def votifierTestPage():
	if not current_user.is_authenticated:
		return render_template("mc/notallowed.html")
	form = VotifierTestForm();
	if(form.validate_on_submit()):
		response = sendVotifierVote(form.ip.data,form.port.data,form.username.data,request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr),form.token.data)
		if(response[0]):
			flash(response[1],"success")
		else:
			flash(response[1],"danger")
		return(redirect(url_for("MCRoutes.votifierTestPage")))
	return render_template('mc/votifiertest.html', form=form)

@MCRoutes.route(prefix+"googlelogin/callback",methods=['GET','POST'])
def googleLoginCallbackPage():
    # Get authorization code Google sent back to you
	code = request.args.get("code")
	# Find out what URL to hit to get tokens that allow you to ask for
	# things on behalf of a user
	google_provider_cfg = get_google_provider_cfg()
	token_endpoint = google_provider_cfg["token_endpoint"]

	baseUrl = request.base_url
	url= request.url
	if request.base_url.startswith('http://'):
		baseUrl = request.base_url.replace('http://', 'https://', 1)
		url = request.url.replace('http://', 'https://', 1)

	# Prepare and send a request to get tokens! Yay tokens!
	token_url, headers, body = client.prepare_token_request(
		token_endpoint,
		authorization_response=url,
		redirect_url=baseUrl,
		code=code
	)
	token_response = requests.post(
		token_url,
		headers=headers,
		data=body,
		auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
	)

	# Parse the tokens!
	client.parse_request_body_response(json.dumps(token_response.json()))

	# Now that you have tokens (yay) let's find and hit the URL
	# from Google that gives you the user's profile information,
	# including their Google profile image and email
	userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
	uri, headers, body = client.add_token(userinfo_endpoint)
	userinfo_response = requests.get(uri, headers=headers, data=body)

	# You want to make sure their email is verified.
	# The user authenticated with Google, authorized your
	# app, and now you've verified their email through Google!
	if userinfo_response.json().get("email_verified"):
		unique_id = userinfo_response.json()["sub"]
		users_email = userinfo_response.json()["email"]
		users_name = userinfo_response.json()["given_name"]
		accountExists = Account.query.filter_by(email=users_email).first()

		if(accountExists is None):
			newUsername = str(unique_id)+str(users_name)
			newAccount = Account(username=newUsername,email=users_email)
			newAccount.isGoogle=True
			newAccount.emailConfirmed = 1
			db.session.add(newAccount)
			db.session.commit()
			#flash("Registered new account!","success") -removed cause there was no page where this was showing 
			#TODO \/ Redirect to profile page not home
			login_user(newAccount, remember=True,force=True)
			return redirect(url_for("MCRoutes.MCHomePage"))
		else:
			if(accountExists.emailConfirmed == 0):
				accountExists.emailConfirmed = 1
				db.session.commit()
			login_user(accountExists, remember=True,force=True)
			return redirect(url_for("MCRoutes.MCHomePage"))

	else:
		flash("In order to login with Google you need to verify your email address on your Google Account.","danger")
		return redirect(url_for("MCRoutes.loginPage"))


@MCRoutes.route(prefix+"addserver",methods=['GET','POST'])
def addServerPage():
	if not current_user.is_authenticated:
		return render_template("mc/notallowed.html")
	form = ServerForm()
	form.isEdit.data="N"
	if form.validate_on_submit():
		response = validateServer(form.ip.data,form.port.data,form.votifierEnabled.data,form.votifierPort.data,request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr),form.votifierToken.data)
		if(response[0] == False):
			flash(response[1],"danger")
		else:
			mcdetails = response[2]
			user = current_user
			email = user.email
			if(user is not None and user.id == current_user.id):
				bannerURL = form.banner.data;

				server = Server(owner=user,verified=0)
				UpdateServerWithForm(form,server)
				db.session.add(server)
				db.session.flush()
				db.session.refresh(server)

				if(bannerURL != ""):
					Live_Banner_URL = os.path.join(APP_ROOT,"static"+url_for('static',filename='images/banners/live')+"/");
					im = Image.open(bannerURL)
					newPath = Live_Banner_URL+str(server.id)+".webp";
					if(im.format == "GIF"):
						# Get sequence iterator
						frames = ImageSequence.Iterator(im)

						# Wrap on-the-fly thumbnail generator
						def thumbnails(frames):
							for frame in frames:
								thumbnail = frame.copy()
								thumbnail.thumbnail((498,60),Image.ANTIALIAS)
								yield thumbnail

						frames = thumbnails(frames)
						om = next(frames)
						om.info = im.info
						om.save(newPath,'webp',quality=80,save_all=True, loop=0,append_images=list(frames))
					else:
						im = im.resize(size=(498,60))
						im.save(newPath,'webp',quality=80)

					server.banner=url_for('static',filename='images/banners/live')+"/"+str(server.id)+".webp?1"

				server.rank=server.id
				server.version = mcdetails['server']['name']
				server.displayVersion = getVersion(mcdetails['server']['name'])
				server.playerCount = mcdetails['players']['now']
				server.playerMax = mcdetails['players']['max']
				server.icon = mcdetails['favicon']
				db.session.commit()
				updateTagRequests(email,server.tags,server.plugins,server.mods,server.datapacks)
				flash('Your server has been submitted for review!',"success")
				redirect(url_for('MCRoutes.MCHomePage'))
			else:
				flash("Invalid session, please log in again.","danger")
	else:
		for key in form.errors:
			flash(form.errors[key][0],"danger")
	return render_template("mc/addServer.html", form=form)

@login_required
@MCRoutes.route(prefix+"editserver/<serverid>",methods=['GET','POST'])
def editServerPage(serverid):
	if(serverid is None):
		return redirect(url_for("MCRoutes.serversPage"))
	server = Server.query.filter_by(id=serverid).first()
	if(server is None or server not in current_user.servers):
		return redirect(url_for("MCRoutes.serversPage"))
	if(server.verified != 1 and server.verified != 2):
		flash("You cannot edit a server whilst it is being reviewed.","warning")
		return redirect(url_for("MCRoutes.serversPage"))
	form = ServerForm()
	form.isEdit.data="Y"
	if form.validate_on_submit():
		response = validateServer(form.ip.data,form.port.data,form.votifierEnabled.data,form.votifierPort.data,request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr),form.votifierToken.data)
		if(response[0] == False):
			flash(response[1],"danger")
		else:
			mcdetails = response[2]
			user = current_user
			if(user is not None and user.id == current_user.id):
				bannerURL = form.banner.data;

				UpdateServerWithForm(form,server)
				if(bannerURL != ""):
					Live_Banner_URL = os.path.join(APP_ROOT,"static"+url_for('static',filename='images/banners/live')+"/");

					im = Image.open(bannerURL)
					newPath = Live_Banner_URL+str(server.id)+".webp";
					if os.path.isfile(newPath):
						os.remove(newPath)

					if(im.format == "GIF"):
						# Get sequence iterator
						frames = ImageSequence.Iterator(im)

						# Wrap on-the-fly thumbnail generator
						def thumbnails(frames):
							for frame in frames:
								thumbnail = frame.copy()
								thumbnail.thumbnail((498,60),Image.ANTIALIAS)
								yield thumbnail

						frames = thumbnails(frames)
						om = next(frames)
						om.info = im.info
						om.save(newPath,'webp',quality=80,save_all=True, loop=0, append_images=list(frames))
					else:
						im = im.resize(size=(498,60))
						im.save(newPath,'webp',quality=80)

					end = int(server.banner.split('?')[1])+1
					server.banner=url_for('static',filename='images/banners/live')+"/"+str(server.id)+".webp?"+str(end)
				
				server.rank=server.id
				server.version = mcdetails['server']['name']
				server.playerCount = mcdetails['players']['now']
				server.playerMax = mcdetails['players']['max']
				server.icon = mcdetails['favicon']
				if(server.verified == 2):
					server.verified = 3
				db.session.commit()
				updateTagRequests(current_user,server.tags,server.plugins,server.mods,server.datapacks)
				if(server.verified == 3):
					flash('Your server has been resubmitted for verification.',"success")
				else:
					flash('Your server has been updated.',"success")
				return redirect(url_for('MCRoutes.serversPage'))
			else:
				flash("Invalid session, please log in again.","danger")
	else:
		for key in form.errors:
			flash(form.errors[key][0],"danger")

	return render_template("mc/editServer.html", form=form, server=server)

@MCRoutes.route(prefix+"account",methods=['GET'])
def accountPage():
	usernameForm = AccountUsernameChangeForm()
	emailForm = AccountEmailChangeForm()
	passwordForm = AccountPasswordChangeForm()
	googleForm = AccountGoogleLinkForm();

	return render_template("mc/account.html",account=current_user,usernameForm=usernameForm,emailForm=emailForm,passwordForm=passwordForm,googleForm=googleForm)

@MCRoutes.route(prefix+"accountusername",methods=['POST'])
def accountChangeUsernamePage():
	usernameForm = AccountUsernameChangeForm()
	if(usernameForm.validate()):
		if(current_user.check_password(usernameForm.password.data)):
			current_user.username = usernameForm.newUsername.data
			db.session.commit()
			flash("Successfully changed the username for the account.","success")
		else:
			flash("Incorrect password.","danger")
	else:
		for key in usernameForm.errors:
			flash(usernameForm.errors[key][0],"danger")
	return redirect(url_for("MCRoutes.accountPage"))

@MCRoutes.route(prefix+"accountemail",methods=['POST'])
def accountChangeEmailPage():
	emailForm = AccountEmailChangeForm()
	if(emailForm.validate()):
		if(current_user.check_password(emailForm.emailPassword.data)):
			current_user.email = emailForm.newEmail.data
			#TODO - VERIFY EMAIL
			db.session.commit()
			flash("Successfully changed the email for the account.","success")
		else:
			flash("Incorrect password.","danger")
	else:
		for key in emailForm.errors:
			flash(emailForm.errors[key][0],"danger")
	return redirect(url_for("MCRoutes.accountPage"))

@MCRoutes.route(prefix+"accountpassword",methods=['POST'])
def accountChangePasswordPage():
	passwordForm = AccountPasswordChangeForm()
	if(passwordForm.validate()):
		if(current_user.check_password(passwordForm.currentPassword.data)):
			current_user.set_password(passwordForm.newPassword.data)
			#TODO - VERIFY EMAIL
			db.session.commit()
			flash("Successfully changed the password for the account.","success")
		else:
			flash("Incorrect password.","danger")
	else:
		for key in passwordForm.errors:
			flash(passwordForm.errors[key][0],"danger")
	return redirect(url_for("MCRoutes.accountPage"))


@MCRoutes.route(prefix+"accountlinkgoogle",methods=['POST'])
def accountLinkGooglePage():
	linkForm = AccountGoogleLinkForm()
	if(linkForm.validate()):
		if(current_user):
			current_user.set_password(linkForm.newPassword.data)
			current_user.username=linkForm.newUsername.data
			current_user.isGoogle = False
			db.session.commit()
			flash("Successfully created a Server List Account","success")
		else:
			flash("Invalid session. Please try again","danger")
	else:
		for key in linkForm.errors:
			flash(linkForm.errors[key][0],"danger")
	return redirect(url_for("MCRoutes.accountPage"))

@login_required
@MCRoutes.route(prefix+"downloaddata",methods=['GET'])
def downloadDataPage():
	if(current_user.lastDataDownload == None or current_user.lastDataDownload < datetime.datetime.now()-datetime.timedelta(hours=1)):
		current_user.lastDataDownload = datetime.datetime.now()
		db.session.commit()
		sendData(current_user)
		flash("Your data will be emailed to you shortly.","success")
	else:
		flash("We have already sent you your data recently. Please check your email.","danger")
	return redirect(url_for("MCRoutes.accountPage"))

@login_required
@MCRoutes.route(prefix+"retrievedata",methods=['GET'])
def retrieveDataPage():
	url = "./application/data/"+str(current_user.id)+".json"
	if( os.path.isfile(url)):
		return send_file("data/"+str(current_user.id)+".json")
	else:
		flash("Unable to find your data file, please send another request. Your link expires after 2 Days.","danger")
	return redirect(url_for("MCRoutes.accountPage"))

@login_required
@MCRoutes.route(prefix+"deleteaccount",methods=['GET','POST'])
def accountDeletePage():
	deleteForm = AccountDeleteForm()
	if(deleteForm.validate_on_submit()):
		if((current_user.isGoogle == False and deleteForm.confirmEmail.data == current_user.email and current_user.check_password(deleteForm.confirmPassword.data)) or (current_user.isGoogle and deleteForm.confirmEmail.data == current_user.email)):
			for server in current_user.servers:
				db.session.delete(server)
			db.session.delete(current_user)
			db.session.commit()
			logout_user()
			flash("Successfully deleted account.","success")
			return redirect(url_for("MCRoutes.loginPage"))
		else:
			flash("Either the account email or password provided was incorrect.","warning")
	else:
		for key in deleteForm.errors:
			flash(deleteForm.errors[key][0],"danger")
	return render_template("mc/deleteaccount.html",deleteForm=deleteForm)

@login_required
@MCRoutes.route(prefix+"deleteserver/<serverid>",methods=['GET','POST'])
def serverDeletePage(serverid):
	deleteForm = ServerDeleteForm()
	server = Server.query.filter_by(id=serverid).first()
	if(serverid is None or server is None):
		return redirect(url_for("MCRoutes.serversPage"))

	if(deleteForm.validate_on_submit()):
		if(deleteForm.confirmName.data == server.name):
			current_user.servers.remove(server)
			db.session.commit()
			flash("Successfully deleted server.","success")
			return redirect(url_for("MCRoutes.serversPage"))
		else:
			flash("The server name was not correct.","warning")
	else:
		for key in deleteForm.errors:
			flash(deleteForm.errors[key][0],"danger")
	return render_template("mc/deleteServer.html",deleteForm=deleteForm,server=server)

@MCRoutes.route(prefix+"privacy",methods=['GET'])
def privacyPolicyPage():
	return policyDetails();

#Temporary until google accepts consent screen
@MCRoutes.route("/privacy",methods=['GET'])
def privacyPolicy2Page():
	return policyDetails();
	

def policyDetails():
	return render_template("mc/privacy.html")

@MCRoutes.route(prefix+"terms",methods=['GET'])
def termsPage():
	return termsDetails();

#Temporary until google accepts consent screen
@MCRoutes.route("/terms",methods=['GET'])
def terms2Page():
	return termsDetails();
	

def termsDetails():
	return render_template("mc/terms.html")

@MCRoutes.route(prefix+"server/<serverid>",methods=['GET'])
def viewServerPage(serverid):
	server = Server.query.get(int(serverid))
	if(server is not None):
		return render_template("mc/viewserver.html",server=server)
	else:
		return redirect(url_for("MCRoutes.MCHomePage"))

@MCRoutes.route(prefix+"ping/<serverid>",methods=['GET'])
def pingServerPage(serverid):
	server = Server.query.get(int(serverid))
	if(server is not None):
		update_server_details(server,True)
		flash("Forcefully pinged server. Your details should now be updated.","success")
	return redirect(url_for("MCRoutes.serversPage"))

@MCRoutes.route(prefix+"server/<serverid>/vote",methods=['GET','POST'])
def serverVotePage(serverid):
	server = Server.query.get(int(serverid))
	if(server is not None):
		_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr).split(',')[0]
		vote = Vote.query.filter_by(serverID=server.id,ip = _ip).first()
		if(vote is not None):
			flash("Already voted for today. Please come back later.","warning")
			return redirect(url_for("MCRoutes.viewServerPage",serverid=serverid))
		form = VoteForm()
		if(request.method == "POST"):
			if(form.validate_on_submit()):
				if("g-recaptcha-response" in request.form):
					token = request.form["g-recaptcha-response"]
					if(verifyCaptcha(token)):
						hasVoted,message = checkHasVoted(_ip,form.username.data,server.id)
						if(hasVoted == False):
							submitVote(server,form.username.data,_ip)
							flash("Successfully voted for server.","success")
							return redirect(url_for("MCRoutes.viewServerPage",serverid=serverid))
						else:
							flash(message,"warning")
					else:
						flash("Invalid captcha, are you sure your not a robot?","warning")
			else:
				for key in form.errors:
					flash(form.errors[key][0],"danger")	
		return render_template("mc/voteserver.html",server=server,form=form)
	else:
		return redirect(url_for("MCRoutes.MCHomePage"))