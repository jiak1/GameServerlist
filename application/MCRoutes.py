from flask import request, render_template,Blueprint,redirect,flash,url_for,send_file
from .Program import mc_db as db,mc_login as login,client,mc_crontab as crontab
from flask_login import current_user, login_user,logout_user, login_required
import os
from .Forms import LoginForm,RegisterForm,ServerForm,ResetPasswordForm,VotifierTestForm,AccountEmailChangeForm,AccountPasswordChangeForm,VoteForm,AccountUsernameChangeForm,AccountGoogleLinkForm,AccountDeleteForm,ServerDeleteForm,ReportServerForm
from .Models import Account, Server,Vote,Report
from .Util import UpdateServerWithForm,update_server_details, send_password_reset_email,send_username_reminder_email, getVersion,get_google_provider_cfg,sendVotifierVote,validateServer,sendData,updateTagRequests,verifyCaptcha,checkHasVoted,submitVote,sendConfirmEmail,sendChangeEmail,ValidUsername,getSuggestionCacheNum,ServerHasQuery,send_email,download_image
from .Config import getProduction,GOOGLE_CLIENT_ID,GOOGLE_CLIENT_SECRET,POSTS_PER_PAGE
import requests
import json
import datetime
from PIL import Image,ImageSequence
import io

MCRoutes = Blueprint('MCRoutes', __name__)
curDir = os.path.dirname(os.path.realpath(__file__))
APP_ROOT = os.path.dirname(os.path.abspath(__file__))

SUGGESTION_CACHE_NUM = getSuggestionCacheNum()

if(getProduction() == False):
	fName = "images/banners/testing"
	Live_Banner_URL = os.path.join("https://testing.server-lists.com/images/banners/testing");
	Initial_Banner_URL = APP_ROOT+"/static/images/banners/testing/";
else:
	fName = "images/banners/live"
	Live_Banner_URL = APP_ROOT+"/static/images/banners/live/";
	Initial_Banner_URL = APP_ROOT+"/static/images/banners/initial/";

prefix = "/"
if(getProduction() == False):
	print("TO CONNECT GO TO testing.server-lists.com/minecraft/")
	prefix = "/minecraft/" 

from .ErrorHandler import *

@MCRoutes.route(prefix+"API/FIXFUCKUP",methods=['GET'])
def APIFIXFUCKUP():
	servers = db.session.query(Server).all()
	for server in servers:
		print(server.name)
		try:
			if(server.initialBanner[0:8] == "/images/"):
				server.initialBanner = "/static"+server.initialBanner
			else:
				splitted = server.initialBanner.split("banners")
				if(splitted[0] == "https://cdn.statically.io/img/minecraft.server-lists.com/images/"):
					server.initialBanner = "https://cdn.statically.io/img/minecraft.server-lists.com/static/images/banners"+splitted[1]
			if(server.banner[0:8] == "/images/"):
				server.banner = "/static"+server.banner
			else:
				splitted = server.banner.split("banners")
				if(splitted[0] == "https://cdn.statically.io/img/minecraft.server-lists.com/images/"):
					server.banner = "https://cdn.statically.io/img/minecraft.server-lists.com/static/images/banners"+splitted[1]
		except:
			pass
	db.session.commit()
	return "done"


@crontab.job(minute="*/5")
def updateCacheNum():
	global SUGGESTION_CACHE_NUM
	SUGGESTION_CACHE_NUM = getSuggestionCacheNum()

@MCRoutes.route(prefix,methods=['GET'])
def MCHomePage():
	page = request.args.get('page', 1, type=int)
	search = request.args.get('search', "")
	canonURL="https://minecraft.server-lists.com"
	_term = "Top Servers"
	try:
		servers,total = Server.search(search,page,POSTS_PER_PAGE)

		if total > page * POSTS_PER_PAGE:
			next_url = url_for('MCRoutes.MCHomePage', search=search, page=page + 1)
		else:
			next_url=None

		if page > 1:
			title = f"Page {page} - Minecraft Server Lists"
			prev_url = url_for('MCRoutes.MCHomePage', search=search, page=page - 1)
		else:
			title = "Minecraft Server Lists"
			prev_url=None
		if(search != ""):
			_term = "Search Results"
			canonURL="https://minecraft.server-lists.com?search="+search
		
		return render_template("mc/index.html",servers=servers,search=search,next_url=next_url,prev_url=prev_url,cacheNum=SUGGESTION_CACHE_NUM,title=title,description="Find top Minecraft Servers using our Minecraft Server List to find a Server that you want to play on, whether that be Survival, Creative or much more!",canonURL=canonURL,searchTerm=_term)
	except Exception as e:
		print(e)
		#runs if we go to an invalid page
		return redirect(url_for("MCRoutes.MCHomePage",search=search))

@MCRoutes.route(prefix+"tag/<string:tagname>",methods=['GET'])
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
			title = tagname+" Minecraft Servers - Page "+str(page)
			prev_url = url_for('MCRoutes.tagSearchPage',tagname=tagname, page=page - 1)
		else:
			title = tagname+" Minecraft Servers"
			prev_url=None
		return render_template("mc/index.html",servers=servers,search=search,next_url=next_url,prev_url=prev_url,cacheNum=SUGGESTION_CACHE_NUM,title=title,description="Browse top "+str(tagname)+" servers on our Minecraft Server List to find one that you want to play on and join loads of other players!",canonURL="https://minecraft.server-lists.com/tag/"+tagname,searchTerm=tagname+" Servers")
	except:
		#runs if we go to an invalid page
		return redirect(url_for("MCRoutes.tagSearchPage",search=tagname))

@MCRoutes.route(prefix+"tags",methods=['GET'])
def tagsPage():
	return render_template("mc/tags.html",search="",cacheNum=SUGGESTION_CACHE_NUM)	

@MCRoutes.route(prefix+"login",methods=['GET', 'POST'])
def loginPage():
	if current_user.is_authenticated: #Flask Login Keeps Track Of Current User
		 return redirect(url_for('MCRoutes.MCHomePage'))

	form = LoginForm() #Use Flask Forms To Retrieve The Post Info & Validate

	if form.validate_on_submit(): #Validate Login Info (Correct Data Type & Size etc)
		#Query Database
		user = Account.query.filter_by(username=form.username.data).first()
		#Check Account Exists
		if user is None or not user.check_password(form.password.data):
			flash('Invalid username or password',"danger")
			return redirect(url_for('MCRoutes.loginPage'))
		#Check If Email Is Confirmed
		if(user.emailConfirmed == 0):
			return redirect(url_for("MCRoutes.emailConfirmationPage"))
		#Simply Login User :D
		login_user(user, remember=form.remember_me.data)
		return redirect(url_for('MCRoutes.MCHomePage'))

	return render_template('mc/login.html', form=form) 
	#Show Login Form If Not Posting

@MCRoutes.route(prefix+"googlelogin",methods=['GET'])
def googleLoginPage():
	google_provider_cfg = get_google_provider_cfg()
	authorization_endpoint = google_provider_cfg["authorization_endpoint"]
    
	url = request.base_url
	if request.base_url.startswith('http://'):
		url = request.base_url.replace('http://', 'https://', 1)

    # Use library to construct the request for Google login and provide
    # scopes that let you retrieve user's profile from Google
	request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri=url+"/callback",
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

@MCRoutes.route(prefix+"servers",methods=['GET'])
@login_required
def serversPage():
	servers = current_user.servers
	if(servers.count() == 0):
		return redirect(url_for("MCRoutes.addServerPage"))
	return render_template("mc/myServers.html", servers=servers)

@MCRoutes.route(prefix+"server",methods=['GET'])
def serverInfoPage():
	return "Works"

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
				if(account.passwordChangeSent < datetime.datetime.now()-datetime.timedelta(minutes=1)):
					account.passwordChangeSent = datetime.datetime.now()
					db.session.commit()
					send_password_reset_email(account)
					flash('Check your email for instructions on how to reset your password.',"success")
				else:
					flash("We have already recently sent you an email. Please check your inbox as well as your Spam and Junk folders.","danger")
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
				if(account.usernameChangeSent < datetime.datetime.now()-datetime.timedelta(minutes=1)):
					account.usernameChangeSent = datetime.datetime.now()
					db.session.commit()
					send_username_reminder_email(account)
					flash('Check your email for your username.',"success")
				else:
					flash("We have already recently sent you an email. Please check your inbox as well as your Spam and Junk folders.","danger")
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
		return render_template("mc/nologinaddserver.html")
	form = ServerForm()
	form.isEdit.data="N"
	if form.validate_on_submit():
		response = validateServer(form.ip.data,form.port.data,form.votifierEnabled.data,form.votifierPort.data,request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr),form.votifierToken.data,form.votifierIP.data)
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
					fExt = bannerURL.split(".")[-1]
					newPath = Live_Banner_URL+str(server.id)+"."+fExt;

					os.replace(bannerURL,newPath)#images/banners/temp
					tempPath = "https://cdn.statically.io/img/minecraft.server-lists.com/static/images/banners/live/"+str(server.id)+"."+fExt+"?w=498&h=60&quality=100&cache=1"
					server.banner=tempPath

					try:
						nonWebpPath = "https://cdn.statically.io/img/minecraft.server-lists.com/static/images/banners/live/"+str(server.id)+"."+fExt+"?w=498&h=60&q=100&cache=1"

						tempDIR = Initial_Banner_URL+"TEMP_"+str(server.id)+"."+fExt

						download_image(nonWebpPath,tempDIR)
						im = Image.open(tempDIR)
						if(fExt.lower() == "gif" or fExt.lower() == "webp"):
							frame = im.convert("RGB")
							frame.save(Initial_Banner_URL+str(server.id)+".png","png")
							fExt = "png"
							im.close()
						else:
							im.save(Initial_Banner_URL+str(server.id)+"."+fExt)
							im.close()

						if os.path.isfile(tempDIR):
							os.remove(tempDIR)

						server.initialBanner = "https://cdn.statically.io/img/minecraft.server-lists.com/static/images/banners/initial/"+str(server.id)+"."+fExt+"?w=498&h=60&q=100&cache=1"
					except:
						server.initialBanner = "/images/main/LoadingBanner.webp"
					
				queryOn = ServerHasQuery(server.ip,server.port)
				server.queryOn = queryOn
				server.rank=server.id
				server.version = mcdetails['server']['name']
				server.displayVersion = getVersion(mcdetails['server']['name'])
				server.playerCount = mcdetails['players']['now']
				server.playerMax = mcdetails['players']['max']
				if("favicon" in mcdetails):
					server.icon = mcdetails['favicon']
				db.session.commit()
				updateTagRequests(email,server.tags,server.plugins,server.mods,server.datapacks)
				flash('Your server has been submitted for review!',"success")
				send_email("NEW SERVER REVIEW","contact@server-lists.com",['jackdonaldson005@gmail.com'],"NEW SERVER TO REVIEW","<h1>NEW SERVER TO REVIEW</h1><br><a href='https://admin.server-lists.com/reviews'>CLICK HERE</a>")
				redirect(url_for('MCRoutes.MCHomePage'))
			else:
				flash("Invalid session, please log in again.","danger")
	else:
		for key in form.errors:
			flash(form.errors[key][0],"danger")
	return render_template("mc/addServer.html", form=form,cacheNum=SUGGESTION_CACHE_NUM)

@MCRoutes.route(prefix+"editserver/<serverid>",methods=['GET','POST'])
@login_required
def editServerPage(serverid):
	if(serverid is None):
		return redirect(url_for("MCRoutes.serversPage"))
	server = Server.query.filter_by(id=serverid).first()
	if(server is None or (server not in current_user.servers and current_user.email != "jackdonaldson005@gmail.com")):
		return redirect(url_for("MCRoutes.serversPage"))
	if(server.verified != 1 and server.verified != 2):
		flash("You cannot edit a server whilst it is being reviewed.","warning")
		return redirect(url_for("MCRoutes.serversPage"))
	if(server.verified == 10):
		flash("This server is banned.","warning")
		return redirect(url_for("MCRoutes.serversPage"))		
	form = ServerForm()
	form.isEdit.data="Y"
	if form.validate_on_submit():
		response = validateServer(form.ip.data,form.port.data,form.votifierEnabled.data,form.votifierPort.data,request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr),form.votifierToken.data,form.votifierIP.data)
		if(response[0] == False):
			flash(response[1],"danger")
		else:
			mcdetails = response[2]
			user = current_user
			if(user is not None and user.id == current_user.id):
				bannerURL = form.banner.data;

				UpdateServerWithForm(form,server)
				if(bannerURL != ""):

					fExt = bannerURL.split(".")[-1]
					newPath = Live_Banner_URL+str(server.id)+"."+fExt;
					os.replace(bannerURL,newPath)#images/banners/temp
					try:
						end = int(server.banner.split('cache=')[-1])+1
					except:
						end = "1"
					
					tempPath = "https://cdn.statically.io/img/minecraft.server-lists.com/static/images/banners/live/"+str(server.id)+"."+fExt+"?w=498&h=60&q=100&f=auto&cache="+str(end)
					server.banner=tempPath

					try:
						nonWebpPath = "https://cdn.statically.io/img/minecraft.server-lists.com/static/images/banners/live/"+str(server.id)+"."+fExt+"?w=498&h=60&q=100&cache="+str(end)

						tempDIR = Initial_Banner_URL+"TEMP_"+str(server.id)+"."+fExt

						download_image(nonWebpPath,tempDIR)
						im = Image.open(tempDIR)
						if(fExt.lower() == "gif" or fExt.lower() == "webp"):
							frame = im.convert("RGB")
							frame.save(Initial_Banner_URL+str(server.id)+".png","png")
							fExt = "png"
							im.close()
						else:
							im.save(Initial_Banner_URL+str(server.id)+"."+fExt)
							im.close()

						if os.path.isfile(tempDIR):
							os.remove(tempDIR)

						server.initialBanner = "https://cdn.statically.io/img/minecraft.server-lists.com/static/images/banners/initial/"+str(server.id)+"."+fExt+"?w=498&h=60&q=100&cache="+str(end)
					except:
						server.initialBanner = "/images/main/LoadingBanner.webp"

				queryOn = ServerHasQuery(server.ip,server.port)
				server.queryOn = queryOn
				server.version = mcdetails['server']['name']
				server.playerCount = mcdetails['players']['now']
				server.playerMax = mcdetails['players']['max']
				if("favicon" in mcdetails):
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

	return render_template("mc/editServer.html", form=form, server=server,cacheNum=SUGGESTION_CACHE_NUM)

@MCRoutes.route(prefix+"account",methods=['GET'])
@login_required
def accountPage():
	usernameForm = AccountUsernameChangeForm()
	emailForm = AccountEmailChangeForm()
	passwordForm = AccountPasswordChangeForm()
	googleForm = AccountGoogleLinkForm();

	return render_template("mc/account.html",account=current_user,usernameForm=usernameForm,emailForm=emailForm,passwordForm=passwordForm,googleForm=googleForm)

@MCRoutes.route(prefix+"accountusername",methods=['POST'])
@login_required
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

@MCRoutes.route(prefix+"changeemail/<token>",methods=['GET'])
def changeEmailPage(token):
	user = Account.verify_email_change_token(token)
	if not user:
		flash("Invalid email change token. Did you wait more then 10 minutes?","danger")
	else:
		if(user.changeEmail != ""):
			user.email = user.changeEmail
			user.changeEmail = ""
			db.session.commit()
			flash("You email has been changed.","success")
		else:
			flash("This token has already been used.","danger")			
	return redirect(url_for('MCRoutes.accountPage'))


@MCRoutes.route(prefix+"accountemail",methods=['POST'])
@login_required
def accountChangeEmailPage():
	emailForm = AccountEmailChangeForm()
	if(emailForm.validate()):
		if(current_user.check_password(emailForm.emailPassword.data)):
			if(current_user.lastEmailConfirmSent < datetime.datetime.now()-datetime.timedelta(minutes=1)):
				current_user.changeEmail = emailForm.newEmail.data
				current_user.lastEmailConfirmSent = datetime.datetime.now()
				db.session.commit()
				sendChangeEmail(current_user)
				flash("A link was sent to your new email that you will need to confirm.","success")
			else:
				flash("You have already requested an email change recently. Please check your inbox.","warning")
		else:
			flash("Incorrect password.","danger")
	else:
		for key in emailForm.errors:
			flash(emailForm.errors[key][0],"danger")
	return redirect(url_for("MCRoutes.accountPage"))


@MCRoutes.route(prefix+"accountpassword",methods=['POST'])
@login_required
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
@login_required
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

@MCRoutes.route(prefix+"downloaddata",methods=['GET'])
@login_required
def downloadDataPage():
	if(current_user.lastDataDownload == None or current_user.lastDataDownload < datetime.datetime.now()-datetime.timedelta(hours=1)):
		current_user.lastDataDownload = datetime.datetime.now()
		db.session.commit()
		sendData(current_user)
		flash("Your data will be emailed to you shortly.","success")
	else:
		flash("We have already sent you your data recently. Please check your email.","danger")
	return redirect(url_for("MCRoutes.accountPage"))

@MCRoutes.route(prefix+"retrievedata",methods=['GET'])
@login_required
def retrieveDataPage():
	url = "./application/data/"+str(current_user.id)+".json"
	if( os.path.isfile(url)):
		return send_file("data/"+str(current_user.id)+".json")
	else:
		flash("Unable to find your data file, please send another request. Your link expires after 2 Days.","danger")
	return redirect(url_for("MCRoutes.accountPage"))

@MCRoutes.route(prefix+"deleteaccount",methods=['GET','POST'])
@login_required
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

@MCRoutes.route(prefix+"deleteserver/<serverid>",methods=['GET','POST'])
@login_required
def serverDeletePage(serverid):
	deleteForm = ServerDeleteForm()
	server = Server.query.filter_by(id=serverid).first()
	if(serverid is None or server is None or server.verified != 1):
		return redirect(url_for("MCRoutes.serversPage"))

	if(deleteForm.validate_on_submit()):
		if(deleteForm.confirmName.data == server.name):
			current_user.servers.remove(server)
			db.session.delete(server)
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
	if(server is not None and server.verified == 1):
		return render_template("mc/viewserver.html",server=server)
	else:
		return redirect(url_for("MCRoutes.MCHomePage"))

@MCRoutes.route(prefix+"ping/<serverid>",methods=['GET'])
@login_required
def pingServerPage(serverid):
	server = Server.query.get(int(serverid))

	if(server is None or (server not in current_user.servers and current_user.email != "jackdonaldson005@gmail.com")):
		return redirect(url_for("MCRoutes.serversPage"))

	update_server_details(server,False,True)
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
							if(ValidUsername(form.username.data)):
								submitVote(server,form.username.data,_ip)
								flash("Successfully voted for server.","success")
								return redirect(url_for("MCRoutes.viewServerPage",serverid=serverid))
							else:
								flash("That username is not registered to a paid Minecraft account.","danger")
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

@MCRoutes.route(prefix+"server/<serverid>/report",methods=['GET','POST'])
def serverReportPage(serverid):
	server = Server.query.get(int(serverid))
	if(server is None):
		return redirect(url_for("MCRoutes.MCHomePage"))
	form = ReportServerForm()
	if(form.validate_on_submit()):
		report = Report(serverID=serverid,name=server.name,reason=form.reason.data,description=form.description.data)
		db.session.add(report)
		db.session.commit()
		flash("Successfully reported server","success")
		return redirect(url_for("MCRoutes.viewServerPage",serverid=serverid))
	else:
		for key in form.errors:
			flash(form.errors[key][0],"danger")	

	return render_template("mc/reportserver.html",server=server,form=form)

@MCRoutes.route(prefix+"pinterest-0cb36",methods=['GET'])
def PintrestConfirmation():
	return render_template("admin/pinterest-0cb36.html")

@MCRoutes.route(prefix+"pay",methods=['GET','POST'])
def sponsorPayPage():
	

	return render_template("mc/pay.html")

@MCRoutes.route(prefix+"guides",methods=['GET'])
def guidesPage():
	return render_template("mc/guides.html")

@MCRoutes.route(prefix+"guides/how-to-make-a-minecraft-server",methods=['GET'])
def makeServerPage():
	return render_template("mc/notallowed.html")
	#return render_template("mc/guides/makeServer.html")
