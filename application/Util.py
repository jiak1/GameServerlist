import requests
from .Models import Server,ReviewTag,Vote,Account
from .Forms import ServerForm
from flask_mail import Message
from flask import render_template,url_for
from .Config import GOOGLE_DISCOVERY_URL,ISADMIN
from .SendVote import sendVote
from pathlib import Path
import arrow
import os
from threading import Thread
import json
import datetime
import socket
from mcstatus import MinecraftServer

if(ISADMIN):
	from .Program import admin_mail as mail,admin_app as app
	from .Program import admin_db as db
else:
	from .Program import mc_mail as mail,mc_app as app
	from .Program import mc_db as db

APP_ROOT = os.path.dirname(os.path.abspath(__file__))

def ServerUp(ip,port):
	try:
		if(port != "25565"):
			#TLDR using ping caused weird issues
			MinecraftServer.lookup(ip+":"+port).status(retries=1)
		else:
			MinecraftServer.lookup(ip).status(retries=1)
		return True
	except (socket.timeout, ConnectionRefusedError, ConnectionResetError, OSError):
		return False
	except Exception as e:
		return False

def ServerStatus(ip,port):
	try:
		if(port != "25565"):
			status = MinecraftServer.lookup(ip+":"+port).status(retries=1)
		else:
			status = MinecraftServer.lookup(ip).status(retries=1)
		
		motd = status.description.get("text") if isinstance(status.description, dict) else str(status.description)
		return (True,{
			"server":{
				"name":status.version.name,
				"protocol":status.version.protocol
			},
			"motd":motd,
			"players":{
				"now":status.players.online,
				"max":status.players.max
			},
			"favicon":status.favicon
		})

	except (socket.timeout, ConnectionRefusedError, ConnectionResetError, OSError):
		#Server Offline
		return (False,None);
	except Exception:
		#Server Offline
		return (False,None);

def ServerQuery(ip,port):
	try:
		if(port != "25565"):
			status = MinecraftServer.lookup(ip+":"+port).query(retries=1)
		else:
			status = MinecraftServer.lookup(ip).query(retries=1)
		
		motd = status.description.get("text") if isinstance(status.description, dict) else str(status.description)
		return (True,{
			"server":{
				"name":status.version.name,
				"protocol":status.version.protocol
			},
			"motd":motd,
			"players":{
				"now":status.players.online,
				"max":status.players.max
			},
			"favicon":status.favicon
		})

	except (socket.timeout, ConnectionRefusedError, ConnectionResetError, OSError):
		#Server Offline
		return (False,None);
	except Exception:
		#Server Offline
		return (False,None);

def ServerHasQuery(ip,port):
	return False


def ValidUsername(username):
	response = requests.get("https://api.mojang.com/users/profiles/minecraft/"+username)
	if(response.status_code == 200 and response.json() != None):
		return True
	else:
		return False
		
def UpdateServerWithForm(_serverForm, _serverModel):
	_serverModel.name = _serverForm.name.data
	_serverModel.ip = _serverForm.ip.data
	_serverModel.port = str(_serverForm.port.data)
	_serverModel.country = _serverForm.country.data
	_serverModel.description = _serverForm.description.data
	_serverModel.serverType = _serverForm.serverType.data
	_serverModel.plugins = _serverForm.plugins.data
	_serverModel.datapacks = _serverForm.datapacks.data
	_serverModel.mods = _serverForm.mods.data
	_serverModel.tags = _serverForm.tags.data
	_serverModel.website = _serverForm.website.data
	_serverModel.discord = _serverForm.discord.data
	_serverModel.trailer = _serverForm.trailer.data
	if(_serverForm.votifierEnabled.data == "Enabled"):
		_serverModel.votifierEnabled = 1
	else:
		_serverModel.votifierEnabled = 0
	_serverModel.votifierIP = _serverForm.votifierIP.data	
	_serverModel.votifierPort = _serverForm.votifierPort.data
	_serverModel.votifierToken = _serverForm.votifierToken.data
	if(str(_serverForm.port.data) != "25565"):
		_serverModel.displayIP = _serverForm.ip.data+":"+str(_serverForm.port.data)
	else:
		_serverModel.displayIP = _serverForm.ip.data

def send_email(subject,sender,recipients,text_body,html_body):
	msg = Message(subject, sender=("Minecraft Server Lists",sender), recipients=recipients)
	msg.body = text_body
	msg.html = html_body
	Thread(target=send_async_email, args=(app, msg)).start()

def send_async_email(app, msg):
	with app.app_context():
		mail.send(msg)
		return

def updateTagRequests(email,tags,plugins,mods,datapacks):
	did1 = checkTags('tags',tags,email)
	did2 = checkTags('plugins',plugins,email)
	did3 = checkTags('mods',mods,email)
	did4 = checkTags('datapacks',datapacks,email)
	if(did1 or did2 or did3 or did4):
		db.session.commit()

def checkTags(section,given,email):
	did = False
	tags = ReviewTag.query.filter_by(section=section).all()
	pending = []
	for item in tags:
		pending.append(item.tag)
	with open('application/static/json/'+section+'.json', 'r') as f:
		split = given.split(",")
		section_dict = json.load(f)
		for item in split:
			if(item != "" and item not in section_dict and item not in pending):
				review = ReviewTag(tag=item,owner=email,section=section)
				db.session.add(review)
				did=True
	return did

def send_password_reset_email(user):
    token = user.get_reset_password_token()
    send_email('[Serverlist] Reset Your Password',
               sender="contact@server-lists.com",
               recipients=[user.email],
               text_body=render_template('email/reset_password.txt',
                                         user=user, token=token),
               html_body=render_template('email/reset_password.html',
                                         user=user, token=token))

def send_username_reminder_email(user):
    send_email('[Serverlist] Username Reminder',
               sender="contact@server-lists.com",
               recipients=[user.email],
               text_body=render_template('email/remember_username.txt',user=user),
               html_body=render_template('email/remember_username.html',user=user))

def getVersion(version):
	if(" " in version):
		x = version.split(' ')
		return x[1]
	else:
		return version

def get_google_provider_cfg():
	return requests.get(GOOGLE_DISCOVERY_URL).json()

def sendVotifierVote(ip,port,username,userIP,token):
	return sendVote(ip,port,username,userIP,token)

def validateServer(ip,port,votifierEnabled,votifierPort,userIP,token,votifierIP):
	mcup,mcdetails = ServerStatus(ip,str(port));
	if(mcup == False):
		return (False,"Unable to connect to your server, check the ip & port are correct and that it is running.")
	if(votifierEnabled == "Enabled"):
		response = sendVotifierVote(votifierIP,votifierPort,"VotifierTestUsername",userIP,token)
		if(response[0] == False):
			return (False,response[1])
	return [True,"",mcdetails]

bannersTempPath = "./application/static/images/banners/temp"

def cleanupTempBanners():
	app.logger.info('cleaning banners')
	Thread(target=do_cleanup_banners, args=(app,)).start()

def do_cleanup_banners(app):
	with(app.app_context()):
		criticalTime = arrow.now().shift(hours=-8)
		for item in Path(bannersTempPath).glob('*'):
			if item.is_file():
				itemTime = arrow.get(item.stat().st_mtime)
				if itemTime < criticalTime:
					os.remove(item.absolute())
		app.logger.info('finished cleaning banners')
		return

dataTempPath = "./application/data/"
def cleanupTempData():
	app.logger.info('cleaning temp data')
	Thread(target=do_cleanup_temp_data, args=(app,)).start()

def do_cleanup_temp_data(app):
	with(app.app_context()):
		criticalTime = arrow.now().shift(days=-2)
		for item in Path(dataTempPath).glob('*'):
			if item.is_file():
				itemTime = arrow.get(item.stat().st_mtime)
				if itemTime < criticalTime:
					os.remove(item.absolute())
		app.logger.info('finished cleaning temp data')
		return

def sendData(account):
	app.logger.info('sending data')
	Thread(target=send_data, args=(app,account.id)).start()

def send_data(app,accid):
	with app.app_context():
		account = Account.query.get(int(accid))
		servers = account.servers;
		_data = account.serialize()
		_data['servers'] = []
		for server in servers:
			_data['servers'].append(server.serialize())
			_data['votes'] = []
			for vote in server.votes:
				_data['votes'].append(vote.serialize())

		try:
			url = "./application/data/"+str(account.id)+".json"
			if( os.path.isfile(url)):
				os.remove(url)
			with open(url, 'w+') as fp:
				json.dump(_data, fp, indent=4, sort_keys=True, default=str)
		except:
			pass
		send_email('[Serverlist] Download Your Data',
				sender="contact@server-lists.com",
				recipients=[account.email],
				text_body=render_template('email/download_data.txt',
				user=account),
				html_body=render_template('email/download_data.html',
				user=account))
		app.logger.info('finished sending data')
		return

def addNewTags(tags,mods,plugins,datapacks):
	addSection('tags',tags)
	addSection('plugins',plugins)
	addSection('datapacks',datapacks)
	addSection('mods',mods)
	db.session.commit()
	updateSuggestionCacheNum()

def addSection(section,values):
	if(values == ""):
		return
	f = open('application/static/json/'+section+'.json', 'r+')
	json_object = json.load(f)
	for val in values.split(','):
		_tag = ReviewTag.query.filter_by(tag=val).first()
		if(_tag is not None):
			db.session.delete(_tag)
		json_object.append(val)
	f.seek(0)
	json.dump(json_object,f, indent=4)
	f.truncate()
	f.close()
	
_secret = app.config['RECAPTCHA_PRIVATE_KEY']

def verifyCaptcha(token):
	data = {
		"secret":_secret,
		"response":token
	}
	response = requests.post("https://www.google.com/recaptcha/api/siteverify",data=data)
	if(response.ok):
		if(response.json()['success'] == True):
			return True
	return False

def checkHasVoted(_ip,username,serverID):
	vote = Vote.query.filter_by(serverID=serverID,ip = _ip).first()
	if(vote is not None):
		return True, "You have already voted recently. Please come back later."
	vote = Vote.query.filter_by(serverID=serverID,username=username).first()
	if(vote is not None):
		return True, "That username has already recieved a vote today."
	return False,""

def submitVote(server, username,ip):
	vote = Vote(server=server,username=username,ip=ip)
	db.session.add(vote)
	server.monthlyVotes += 1
	server.totalVotes += 1
	db.session.commit()
	if(server.votifierEnabled == 1):
		sendVote(server.votifierIP,server.votifierPort,username,ip,server.votifierToken)

def checkServerUpdates():
	app.logger.info('checking updates')
	Thread(target=do_update_check, args=(app,)).start()

#run once a every 1 minute
def do_update_check(app):
	app.logger.info('pinging servers for updates')
	with app.app_context():
		servers = Server.query.all()
		total = len(servers)
		fourth = round(total/4)+2#Splits them up so we dont ping all servers at once
		_t = datetime.datetime.now()-datetime.timedelta(minutes=5)
		count = 0
		for server in servers:
			if(server.lastPingTime < _t):
				if(count < fourth):
					count += 1
					update_server_details(server)
		app.logger.info('finished checking updates')
		return

def update_server_details(server,forceOn = False,forceIcon = False):
	if(server.queryOn == 0):
		response,stats = ServerStatus(server.ip,server.port)
	else:
		response,stats = ServerQuery(server.ip,server.port)
	server.lastPingTime = datetime.datetime.now()
	if(response):
		#Server Online
		#Set last ping to now
		server.online = 1
		server.playerCount = stats['players']['now']
		server.playerMax = stats['players']['max']
		server.lastOnlineTime = datetime.datetime.now()
		#queryOn = ServerHasQuery(server.ip,server.port)
		#server.queryOn = queryOn
		if(forceIcon and not forceOn):
			if('favicon' in stats):
				server.icon = stats['favicon']
		if(forceOn):
			if('favicon' in stats):
				server.icon = stats['favicon']
			server.displayVersion = getVersion(stats['server']['name'])
		db.session.commit()
	else:
		#Server Offline
		server.online = 0
		server.playerCount = 0
		db.session.commit()

def serverRank():
	app.logger.info('ranking servers')
	Thread(target=do_server_rank, args=(app,)).start()

def do_server_rank(app):
	with(app.app_context()):
		servers = Server.query.order_by(Server.monthlyVotes.desc(),Server.playerCount.desc())
		rank = 1
		for server in servers:
			server.rank = rank
			rank += 1
		db.session.commit()
		app.logger.info('finished ranking')
		return

def disableServers():
	app.logger.info('disabling servers that are still offline')
	Thread(target=do_disable_server_check, args=(app,)).start()

def do_disable_server_check(app):
	with(app.app_context()):
		servers = Server.query.all()
		weekAgo = datetime.datetime.now()-datetime.timedelta(days=7)
		for server in servers:
			if(server.lastOnlineTime < weekAgo):
				server.verified = 2
				server.rejectReason = "Server Was Offline For More Then 7 Days."
		db.session.commit()
		app.logger.info('finished disabling servers')
		return

def UpdateAdminServerWithForm(_serverForm, _serverModel):
	UpdateServerWithForm(_serverForm,_serverModel)
	_serverModel.newTime = datetime.datetime.utcnow()
	_serverModel.rejectReason = _serverForm.rejectReason.data
	_serverModel.version = _serverForm.version.data
	_serverModel.displayVersion = _serverForm.displayVersion.data
	_serverModel.totalVotes = _serverForm.totalVotes.data
	_serverModel.monthlyVotes = _serverForm.monthlyVotes.data
	_serverModel.rank = _serverForm.rank.data
	_serverModel.playerCount = _serverForm.playerCount.data
	_serverModel.playerMax = _serverForm.playerMax.data
	_serverModel.notes = _serverForm.notes.data
	_serverModel.banner = _serverForm.banner.data

def sendServerApprovedEmail(server):
    send_email('[Serverlist] Server Approved',
               sender="contact@server-lists.com",
               recipients=[server.owner.email],
               text_body=render_template('email/server_approved.txt',
                                         server=server),
               html_body=render_template('email/server_approved.html',
                                         server=server))

def sendServerDeniedEmail(server):
    send_email('[Serverlist] Server Denied',
               sender="contact@server-lists.com",
               recipients=[server.owner.email],
               text_body=render_template('email/server_denied.txt',
                                         server=server),
               html_body=render_template('email/server_denied.html',
                                         server=server))

def sendConfirmEmail(user):
	token = user.get_email_confirm_token()
	send_email('[Serverlist] Activate Account',
               sender="contact@server-lists.com",
               recipients=[user.email],
               text_body=render_template('email/confirm_email.txt',
                                         user=user, token=token),
               html_body=render_template('email/confirm_email.html',
                                         user=user, token=token))

def sendChangeEmail(user):
	token = user.get_email_change_token()
	send_email('[Serverlist] Change Email',
               sender="contact@server-lists.com",
               recipients=[str(user.changeEmail)],
               text_body=render_template('email/change_email.txt',
                                         user=user, token=token),
               html_body=render_template('email/change_email.html',
                                         user=user, token=token))

def clearVotes():
	since = datetime.datetime.now() - datetime.timedelta(hours=24)
	votes = (db.session.query(Vote).filter(Vote.voteTime < since))
	for vote in votes:
		db.session.delete(vote)
	db.session.commit()

def getSuggestionCacheNum():
	f = open('application/static/json/cache.txt')
	response = f.readline()
	f.close()
	return response

def updateSuggestionCacheNum():
	nextCacheNum = str(int(getSuggestionCacheNum())+1)

	with open('application/static/json/cache.txt', "r+") as f:
		f.read()
		f.seek(0)
		f.write(nextCacheNum)
		f.truncate()

#every two hours will yield 84 points for a week
def logServerGraphs():
	app.logger.info('logging graphs')
	Thread(target=updateServerGraphs, args=(app,)).start()

def updateServerGraphs(app):
	with app.app_context():
		servers = Server.query.all()
		for server in servers:
			logServer(server)
		app.logger.info('finished graphs')
		return

def logServer(server):
	url = "application/static/json/graphs/"+ str(server.id)+".json"
	if(os.path.isfile(""+url) == False):
		baseData = {
			"players":[]
		}
		with open(url, 'w+') as f:
			json.dump(baseData, f, indent=4, sort_keys=True, default=str)
	if(server.queryOn == 0):
		response,stats = ServerStatus(server.ip,server.port)
	else:
		response,stats = ServerQuery(server.ip,server.port)
	if(response):
		playersNow = int(stats["players"]["now"])
	else:
		playersNow = 0
	with open(url,"r+") as f:
		section_dict = json.load(f)
		#every two hours will yield 84 points for a week
		if(len(section_dict["players"]) >= 84):
			section_dict["players"].pop(0)
		section_dict["players"].append({
			"count":playersNow,
			"time":datetime.datetime.now()
		})
		f.seek(0)
		json.dump(section_dict, f, indent=4, sort_keys=True, default=str)
		f.truncate()

def transitionVotesMonth():
	Thread(target=do_vote_month_change, args=(app,)).start()

def do_vote_month_change(app):
	with(app.app_context()):
		servers = Server.query.all()
		for server in servers:
			server.monthlyVotes = 0
		db.session.commit()

logCount = 0
for file in os.listdir(os.fsencode(APP_ROOT+"/static/logs")):
	logCount+=1
from pympler import summary, muppy
def do_logging():
	mem_summary = summary.summarize(muppy.get_objects())
	rows = summary.format_(mem_summary)
	result = "<h1>"+datetime.datetime.now().strftime("%H:%M:%S")+"</h1><br>"
	for line in rows:
		result = result +"<code>"+line+"</code><br>"

	f = open(APP_ROOT+"/static/logs/"+str(logCount)+".txt","w")
	f.write(result)
	f.close()