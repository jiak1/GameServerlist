from flask import request,Blueprint, jsonify,abort,url_for,redirect
from .Program import mc_db as db
import os
from .Util import ServerUp,ServerStatus,cleanupTempBanners,cleanupTempData,checkServerUpdates, serverRank,clearVotes,logServerGraphs,sendVotifierVote,disableServers,do_logging
from .SendVote import sendVote
from .Models import Server,ReviewTag
from .Program import mc_mail as mail, elasticsearch
from random import randrange
from .Config import IMGDOMAIN,getProduction,ISADMIN,INDEX_CREATION
from pympler import summary, muppy
import time

APIRoutes = Blueprint('APIRoutes', __name__)
curDir = os.path.dirname(os.path.realpath(__file__))
APP_ROOT = os.path.dirname(os.path.abspath(__file__))

prefix="/"
if(getProduction() == False):
	prefix = "/minecraft/" 

if(ISADMIN):
	from .Program import admin_crontab as crontab
else:
	from .Program import mc_crontab as crontab

@APIRoutes.route(prefix+"API/DEBUG",methods=['GET'])
def APIDebug():
	# Only import Pympler when we need it. We don't want it to
	# affect our process if we never call memory_summary.
	mem_summary = summary.summarize(muppy.get_objects())
	rows = summary.format_(mem_summary)
	result = ""
	for line in rows:
		result = result +"<code>"+line+"</code><br>"
	return result

@APIRoutes.route(prefix+"API/PING",methods=['POST'])
def APIPing():
	data = request.get_json();
	ip = data['IP']
	port = data['PORT']

	online = ServerUp(ip,port)
	if(online):
		return jsonify({"STATUS":"ONLINE"})
	else:
		return jsonify({"STATUS":"OFFLINE"})

@APIRoutes.route(prefix+"API/STATUS",methods=['POST'])
def APIStatus():
	data = request.get_json();
	ip = data['IP']
	port = data['PORT']
	response = ServerStatus(ip,port)
	if(response[0]):
		status = response[1]
		return jsonify({"STATUS":"ONLINE",
		"VERSION":status['server']['name'],
		"PROTOCOL":status['server']['protocol'],
		"MOTD":status['motd'],
		"PLAYER_COUNT":status['players']['now'],
		"PLAYER_MAX":status['players']['max']})
	else:
		return jsonify({"STATUS":"OFFLINE"})

@APIRoutes.route(prefix+"API/BANNERUPLOAD",methods=['POST'])
def APIBannerUpload():
	banner=request.files.get('file')
	tempURL = url_for('static',filename='images/banners/temp')
	url = ""+tempURL+"/"+banner.filename;
	if(getProduction()):
		url = os.path.join(APP_ROOT+"/"+tempURL+"/", banner.filename)
	else:
		url = os.path.join(APP_ROOT+tempURL+"/", banner.filename)	
	if os.path.isfile(url):
		#Another file is already called this
		filename,ext = banner.filename.split(".")
		filename += str(randrange(10000,10000000))
		newName = filename+"."+ext
		if(getProduction()):
			url = os.path.join(APP_ROOT+"/"+tempURL+"/", newName)
		else:
			url = os.path.join(APP_ROOT+tempURL+"/", newName)
	banner.save(url)
	return jsonify({"URL":url,"IMGURL":"https://cdn.statically.io/img/minecraft.server-lists.com/static/images/banners/temp/"
	+banner.filename+"?w=498&h=60&quality=100&cache=-1"})

@APIRoutes.route(prefix+"API/VOTIFIER",methods=['POST'])
def APIVotifier():
	data = request.get_json();
	ip = data['IP']
	port = data['PORT']
	token = data['TOKEN']
	response = sendVotifierVote(ip,port,"MCServerListTest",request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr),token)
	result = {
		"STATUS":response[0],
		"MESSAGE":response[1]
	}
	return jsonify(result)

@crontab.job(minute="*/1")
def doUpdate():
	checkServerUpdates()

@crontab.job(minute="*/1")
def doLogging():
	#do_logging()
	pass

@crontab.job(minute="*/5")
def clearVotesCron():
	clearVotes()

@crontab.job(minute="0", hour="*/1")
def doCleanup():
	cleanupTempBanners()
	cleanupTempData()

@crontab.job(minute="8", hour="*/8")
def doRank():
	serverRank()

@crontab.job(minute="5", hour="*/2")
def graphServers():
	logServerGraphs()

@crontab.job(minute="20", hour="*/10")
def doDisableCheck():
	disableServers()

@crontab.job(minute="8", hour="*/23")
def doESReshuffle():
	elasticsearch.indices.delete(index='server', ignore=[400, 404])
	time.sleep(2)#2 seconds
	elasticsearch.indices.create(index='server',body=INDEX_CREATION)
	time.sleep(2)#2 seconds
	Server.reindex()