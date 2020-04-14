from flask import request,Blueprint, jsonify,abort
from .Program import db,login
import os
from .Util import ServerUp,ServerStatus

APIRoutes = Blueprint('APIRoutes', __name__)
curDir = os.path.dirname(os.path.realpath(__file__))

@APIRoutes.route("/minecraft/API/PING",methods=['POST'])
def APIPing():
	data = request.get_json();
	ip = data['IP']
	port = data['PORT']
	online = ServerUp(ip,port)
	if(online):
		return jsonify({"STATUS":"ONLINE"})
	else:
		return jsonify({"STATUS":"OFFLINE"})

@APIRoutes.route("/minecraft/API/STATUS",methods=['POST'])
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

