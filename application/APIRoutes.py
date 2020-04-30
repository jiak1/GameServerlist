from flask import request,Blueprint, jsonify,abort,url_for,redirect
from .Program import mc_db as db
import os
from .Util import ServerUp,ServerStatus,cleanupTempBanners,cleanupTempData,checkServerUpdates, serverRank,clearVotes,logServerGraphs,sendVotifierVote
from .SendVote import sendVote
from .Models import Server,ReviewTag
from .Program import mc_mail as mail, elasticsearch
from random import randrange
from .Config import IMGDOMAIN,getProduction,ISADMIN

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

@APIRoutes.route(prefix+"API/PING",methods=['POST'])
def APIPing():
	data = request.get_json();
	ip = data['IP']
	port = data['PORT']
	print(ip)
	print(port)
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
	url = "static"+tempURL+"/"+banner.filename;
	url = os.path.join(APP_ROOT+"/static"+tempURL+"/", banner.filename)
	if os.path.isfile(url):
		#Another file is already called this
		filename,ext = banner.filename.split(".")
		filename += str(randrange(10000,10000000))
		newName = filename+"."+ext
		url = os.path.join(APP_ROOT+"/static"+tempURL+"/", newName)
	banner.save(url)
	return jsonify({"URL":url,"IMGURL":"https://"+IMGDOMAIN+tempURL+"/"+banner.filename})

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

indexCreation = {
  "settings": {
    "index": {
      "max_ngram_diff": 7
    },
    "analysis": {
      "analyzer": {
        "default": {
          "tokenizer": "keyword",
          "filter": [ 
			  "3_5_grams",
			  "lowercase"
			]
        }
      },
      "filter": {
        "3_5_grams": {
          "type": "ngram",
          "min_gram": 3,
          "max_gram": 10,
		  "token_chars":[
            "letter",
            "digit",
            "symbol"
          ]
        }
      }
    }
  }
}

@crontab.job(minute="*/1")
def doUpdate():
	checkServerUpdates()

@crontab.job(minute="*/5")
def clearVotesCron():
	clearVotes()

@crontab.job(minute="0", hour="*/1")
def doCleanup():
	cleanupTempBanners()
	cleanupTempData()

@crontab.job(minute="0", hour="0",day="*/1")
def doRank():
	serverRank()

@crontab.job(minute="5", hour="*/2")
def graphServers():
	logServerGraphs()