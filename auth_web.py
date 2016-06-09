#! /usr/bin/env python

import cherrypy
import os
from cherrypy.process import servers
import requests
import json
from creds import *
import urllib
import socket

class Start(object):
	def index(self):
		scope="alexa_all"
		sd = json.dumps({
		    "alexa:all": {
		        "productID": ProductID,
		        "productInstanceAttributes": {
		            "deviceSerialNumber": "001"
		        }
		    }
		})
		url = "https://www.amazon.com/ap/oa"
		callback = cherrypy.url()  + "code" 
		payload = {"client_id" : Client_ID, "scope" : "alexa:all", "scope_data" : sd, "response_type" : "code", "redirect_uri" : callback }
		req = requests.Request('GET', url, params=payload)
		p = req.prepare()
		raise cherrypy.HTTPRedirect(p.url)
	def code(self, var=None, **params):
		code = urllib.quote(cherrypy.request.params['code'])
		callback = cherrypy.url()
		payload = {"client_id" : Client_ID, "client_secret" : Client_Secret, "code" : code, "grant_type" : "authorization_code", "redirect_uri" : callback }
		url = "https://api.amazon.com/auth/o2/token"
		r = requests.post(url, data = payload)
		resp = r.json()
		line = 'refresh_token = "{}"'.format(resp['refresh_token'])
		with open("creds.py", 'a') as f:
			f.write(line)
		return "<h2>Success!</h2><h3> Refresh token has been added to your creds file, you may now reboot the Pi </h3><br>{}".format(resp['refresh_token'])
	index.exposed = True
	code.exposed = True
		
cherrypy.config.update({'server.socket_host': '0.0.0.0',})
cherrypy.config.update({'server.socket_port': int(os.environ.get('PORT', '5050')),})
cherrypy.config.update({ "environment": "embedded" })


ip =[(s.connect(('8.8.8.8', 53)), s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]
print "Ready goto http://{}:5050 or http://localhost:5050  to begin the auth process".format(ip) 
cherrypy.quickstart(Start())

