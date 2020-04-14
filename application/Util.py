import requests
from .Models import Server
from .Forms import ServerForm
def ServerUp(ip,port):
	response = requests.get("https://mcapi.us/server/status?ip="+ip+"&port="+port)
	data = response.json() 
	if(data != None and data['status'] == "success" and data["online"] == True):
		return True
	return False

def ServerStatus(ip,port):
	response = requests.get("https://mcapi.us/server/status?ip="+ip+"&port="+port)
	data = response.json()
	if(data != None and data['status'] == "success" and data["online"] == True):
		return True,data
	return (False,None);

def UpdateServerWithForm(_serverForm, _serverModel):
	_serverModel.name = _serverForm.name.data
	_serverModel.ip = _serverForm.ip.data
	_serverModel.port = _serverForm.port.data
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