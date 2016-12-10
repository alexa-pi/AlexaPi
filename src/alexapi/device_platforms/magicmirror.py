from __future__ import print_function
import time
import BaseHTTPServer
import threading
import urllib2
import urlparse

from baseplatform import BasePlatform

# Magic Mirror platform
# -----------------------------------------------------------------------------------------------------------------
# This device platform is made to integrate with the Magic Mirror project: https://github.com/MichMich/MagicMirror
# Specifically, this communicates with the MMM-AlexaPi module: https://github.com/dgonano/MMM-AlexaPi
# The two systems communicate over GET requests which,
# 	- Update the Magic Mirror display with AlexaPi's status (No connection, idle, listening, processing, speaking)
# 	- Allow the Magic Mirror to trigger a 'start listening' request

class MagicmirrorPlatform(BasePlatform):

	def __init__(self, config):
		if config['debug']:
			print("Initialising Magic Mirror platorm")

		super(MagicmirrorPlatform, self).__init__(config, 'magicmirror')

		self.host_name = self._pconfig['hostname']
		self.port_number = self._pconfig['port']
		self.mm_host = self._pconfig['mm_hostname']
		self.mm_port = self._pconfig['mm_port']
		self.hb_timer = self._pconfig['hb_timer']

		self.shutdown = False
		self.req_record = False
		self.httpd = ""
		self.serverthread = ""

	def setup(self):
		if self._config['debug']:
			print("Setting up Magic Mirror platform")
			print(time.asctime(), "Magic Mirror HTTP Server - %s:%s" % (self.host_name, self.port_number))

		# Setup http server
		self.httpd = CallbackHTTPServer((self.host_name, self.port_number), MMHTTPHandler)
		self.httpd.set_callback(self.http_callback)
		self.serverthread = threading.Thread(target=self.httpd.serve_forever)
		self.serverthread.daemon = True

	def indicate_failure(self):
		if self._config['debug']:
			print("Indicating Failure")

		self.update_mm("failure")

	def indicate_success(self):
		if self._config['debug']:
			print("Indicating Success")

		self.update_mm("success")

	def after_setup(self):
		if self._config['debug']:
			print("Starting Magic Mirror platform HTTP Server")

		self.serverthread.start()

		if self._config['debug']:
			print("Starting Magic Mirror heartbeat with " + str(self.hb_timer) + " second interval")

		self.mm_heartbeat()

	def indicate_recording(self, state=True):
		if self._config['debug']:
			print("Indicate Start Recording" if state else "Indicate Stop Recording")

		self.update_mm("recording" if state else "idle")

	def indicate_playback(self, state=True):
		if self._config['debug']:
			print("Indicate Start Playing" if state else "Indicate Stop Playing")

		self.update_mm("playback" if state else "idle")

	def indicate_processing(self, state=True):
		if self._config['debug']:
			print("Indicate Start Processing" if state else "Indicate Stop Processing")

		self.update_mm("processing" if state else "idle")

	def should_record(self):
		record = self.req_record
		self.req_record = False
		return record

	def update_mm(self, status):
		address = ("http://" + self.mm_host + ":" + self.mm_port + "/alexapi?action=AVSSTATUS&status=" + status)

		if self._config['debug']:
			print("Calling URL: " + address)

		try:
			response = urllib2.urlopen(address).read()
		except urllib2.URLError, err:
			print("URLError: ", err.reason)
			return

		if self._config['debug']:
			print("Response: " + response)

	def mm_heartbeat(self):
		# Check if stop or set next timer
		if self.shutdown:
			return
		threading.Timer(self.hb_timer, self.mm_heartbeat).start()

		address = ("http://" + self.mm_host + ":" + self.mm_port + "/alexapi?action=AVSHB")

		if self._config['debug']:
			print("Sending MM Heatbeat")

		try:
			response = urllib2.urlopen(address).read()
		except urllib2.URLError, err:
			print("URLError: ", err.reason)
			return

		if self._config['debug']:
			print("Response: " + response)

	def http_callback(self, query_dict):
		if (query_dict['action'][0] == "requestrecord"):
			self.req_record = True
			return True
		else:
			return False

	def cleanup(self):
		if self._config['debug']:
			print("Cleaning up Magic Mirror platform")

		self.httpd.shutdown()
		self.shutdown = True


# Subclass HTTPServer with additional callback
class CallbackHTTPServer(BaseHTTPServer.HTTPServer):
	def set_callback(self, callback):
		self.RequestHandlerClass.set_callback(callback)

# Subclass Request Handler to use callback
class MMHTTPHandler(BaseHTTPServer.BaseHTTPRequestHandler):
	@classmethod
	def set_callback(cls, callback):
		cls.callback = callback

	def do_HEAD(self): # pylint: disable=invalid-name
		self.send_response(200)
		self.send_header("Content-type", "text/html")
		self.end_headers()

	def do_GET(self): # pylint: disable=invalid-name
		self.send_response(200)
		self.end_headers()

		query = urlparse.urlsplit(self.path).query
		query_dict = urlparse.parse_qs(query)

		if 'action' in query_dict.keys():
			if (self.callback(query_dict)):
				self.wfile.write('{"status":"success"}')
			else:
				self.wfile.write('{"status":"error", "reason":"unknown_action"}')
		else:
			self.wfile.write('{"status":"error", "reason":"unknown_command"}')
