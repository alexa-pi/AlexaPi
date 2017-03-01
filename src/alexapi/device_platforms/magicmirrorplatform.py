import logging
import threading

try:
	import BaseHTTPServer
except ImportError:
	import http.server as BaseHTTPServer

try:
	from urllib.request import urlopen, URLError
	import urllib.urlparse as urlparse
except ImportError:
	from urllib2 import urlopen, URLError
	import urlparse

from .baseplatform import BasePlatform

# Magic Mirror platform
# -----------------------------------------------------------------------------------------------------------------
# This device platform is made to integrate with the Magic Mirror project: https://github.com/MichMich/MagicMirror
# Specifically, this communicates with the MMM-AlexaPi module: https://github.com/dgonano/MMM-AlexaPi
# The two systems communicate over GET requests which,
# 	- Update the Magic Mirror display with AlexaPi's status (No connection, idle, listening, processing, speaking)
# 	- Allow the Magic Mirror to trigger a 'start listening' request

logger = logging.getLogger(__name__)


class MagicmirrorPlatform(BasePlatform):

	def __init__(self, config):
		logger.debug("Initialising Magic Mirror platorm")

		super(MagicmirrorPlatform, self).__init__(config, 'magicmirror')

		self.host_name = self._pconfig['hostname']
		self.port_number = self._pconfig['port']
		self.mm_host = self._pconfig['mm_hostname']
		self.mm_port = self._pconfig['mm_port']
		self.hb_timer = self._pconfig['hb_timer']

		self.shutdown = False
		self.httpd = None
		self.serverthread = None

	def setup(self):
		logger.debug("Setting up Magic Mirror platform")
		logger.info("Magic Mirror HTTP Server - %s:%s", self.host_name, self.port_number)

		# Setup http server
		self.httpd = CallbackHTTPServer((self.host_name, self.port_number), MMHTTPHandler)
		self.httpd.set_callback(self.http_callback)
		self.serverthread = threading.Thread(target=self.httpd.serve_forever)
		self.serverthread.daemon = True

	def indicate_failure(self):
		logger.debug("Indicating Failure")

		self.update_mm("failure")

	def indicate_success(self):
		logger.debug("Indicating Success")

		self.update_mm("success")

	def after_setup(self, trigger_callback=None):

		self._trigger_callback = trigger_callback

		logger.debug("Starting Magic Mirror platform HTTP Server")
		self.serverthread.start()

		logger.debug("Starting Magic Mirror heartbeat with %s second interval", self.hb_timer)
		self.mm_heartbeat()

	def indicate_recording(self, state=True):
		logger.debug("Indicate Start Recording" if state else "Indicate Stop Recording")

		self.update_mm("recording" if state else "idle")

	def indicate_playback(self, state=True):
		logger.debug("Indicate Start Playing" if state else "Indicate Stop Playing")

		self.update_mm("playback" if state else "idle")

	def indicate_processing(self, state=True):
		logger.debug("Indicate Start Processing" if state else "Indicate Stop Processing")

		self.update_mm("processing" if state else "idle")

	def force_recording(self):
		return False

	def update_mm(self, status):
		address = ("http://" + self.mm_host + ":" + self.mm_port + "/alexapi?action=AVSSTATUS&status=" + status)

		logger.debug("Calling URL: %s", address)

		try:
			response = urlopen(address).read()
		except URLError as err:
			logger.error("URLError: %s", err.reason)
			return

		logger.debug("Response: %s", response)

	def mm_heartbeat(self):
		# Check if stop or set next timer
		if self.shutdown:
			return
		threading.Timer(self.hb_timer, self.mm_heartbeat).start()

		address = ("http://" + self.mm_host + ":" + self.mm_port + "/alexapi?action=AVSHB")

		logger.debug("Sending MM Heatbeat")

		try:
			response = urlopen(address).read()
		except URLError as err:
			logger.error("URLError: %s", err.reason)
			return

		logger.debug("Response: " + response)

	def http_callback(self, query_dict):
		if (query_dict['action'][0] == "requestrecord"):

			if self._trigger_callback:
				self._trigger_callback()

			return True
		else:
			return False

	def cleanup(self):
		logger.debug("Cleaning up Magic Mirror platform")

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
