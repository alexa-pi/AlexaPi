#! /usr/bin/env python

import importlib
import os
import logging
import tempfile
import signal
import shutil
import time
import sys
import threading
import json
import optparse
import email
import subprocess
from future.builtins import bytes

import yaml
import requests
import coloredlogs

import alexapi.config
import alexapi.tunein as tunein
import alexapi.capture
import alexapi.triggers as triggers
from alexapi.exceptions import ConfigurationException
from alexapi.constants import RequestType, PlayerActivity

logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s')
coloredlogs.DEFAULT_FIELD_STYLES = {
	'hostname': {'color': 'magenta'},
	'programname': {'color': 'cyan'},
	'name': {'color': 'blue'},
	'levelname': {'color': 'magenta', 'bold': True},
	'asctime': {'color': 'green'}
}
coloredlogs.DEFAULT_LEVEL_STYLES = {
	'info': {'color': 'blue'},
	'critical': {'color': 'red', 'bold': True},
	'error': {'color': 'red'},
	'debug': {'color': 'green'},
	'warning': {'color': 'yellow'}
}

# Get arguments
parser = optparse.OptionParser()
parser.add_option('-s', '--silent',
		dest="silent",
		action="store_true",
		default=False,
		help="start without saying hello")
parser.add_option('-d', '--debug',
		dest="debug",
		action="store_true",
		default=False,
		help="display debug messages")
parser.add_option('--daemon',
		dest="daemon",
		action="store_true",
		default=False,
		help="Used by initd/systemd start script to reconfigure logging")

cmdopts, cmdargs = parser.parse_args()
silent = cmdopts.silent
debug = cmdopts.debug

config_exists = alexapi.config.filename is not None

if config_exists:
	with open(alexapi.config.filename, 'r') as stream:
		config = yaml.load(stream)

if debug:
	log_level = logging.DEBUG
else:
	if config_exists:
		log_level = logging.getLevelName(config.get('logging', 'INFO').upper())
	else:
		log_level = logging.getLevelName('INFO')

if cmdopts.daemon:
	coloredlogs.DEFAULT_LOG_FORMAT = '%(levelname)s: %(message)s'
else:
	coloredlogs.DEFAULT_LOG_FORMAT = '%(asctime)s %(levelname)s: %(message)s'

coloredlogs.install(level=log_level)
alexa_logger = logging.getLogger('alexapi')
alexa_logger.setLevel(log_level)

logger = logging.getLogger(__name__)

if not config_exists:
	logger.critical('Can not find configuration file. Exiting...')
	sys.exit(1)

# Setup event commands
event_commands = {
	'startup': "",
	'pre_interaction': "",
	'post_interaction': "",
	'shutdown': "",
}

if 'event_commands' in config:
	event_commands.update(config['event_commands'])

im = importlib.import_module('alexapi.device_platforms.' + config['platform']['device'] + 'platform', package=None)
cl = getattr(im, config['platform']['device'].capitalize() + 'Platform')
platform = cl(config)


class Player(object):

	config = None
	platform = None
	pHandler = None
	tunein_parser = None

	navigation_token = None
	playlist_last_item = None
	progressReportRequired = []

	def __init__(self, config, platform, pHandler): # pylint: disable=redefined-outer-name
		self.config = config
		self.platform = platform
		self.pHandler = pHandler # pylint: disable=invalid-name
		self.tunein_parser = tunein.TuneIn(5000)

	def play_playlist(self, payload):
		self.navigation_token = payload['navigationToken']
		self.playlist_last_item = payload['audioItem']['streams'][-1]['streamId']

		for stream in payload['audioItem']['streams']: # pylint: disable=redefined-outer-name

			streamId = stream['streamId']
			if stream['progressReportRequired']:
				self.progressReportRequired.append(streamId)

			url = stream['streamUrl']
			if stream['streamUrl'].startswith("cid:"):
				url = "file://" + tmp_path + stream['streamUrl'].lstrip("cid:") + ".mp3"

			if (url.find('radiotime.com') != -1):
				url = self.tunein_playlist(url)

			self.pHandler.queued_play(mrl_fix(url), stream['offsetInMilliseconds'], audio_type='media', stream_id=streamId)

	def play_speech(self, mrl):
		self.stop()
		self.pHandler.blocking_play(mrl)

	def stop(self):
		self.pHandler.stop()

	def is_playing(self):
		return self.pHandler.is_playing()

	def get_volume(self):
		return self.pHandler.volume

	def set_volume(self, volume):
		self.pHandler.set_volume(volume)

	def playback_callback(self, requestType, playerActivity, streamId):
		if (requestType == RequestType.STARTED) and (playerActivity == PlayerActivity.PLAYING):
			self.platform.indicate_playback()
		elif (requestType in [RequestType.INTERRUPTED, RequestType.FINISHED, RequestType.ERROR]) and (playerActivity == PlayerActivity.IDLE):
			self.platform.indicate_playback(False)

		if streamId:
			if streamId in self.progressReportRequired:
				self.progressReportRequired.remove(streamId)
				gThread = threading.Thread(target=alexa_playback_progress_report_request, args=(requestType, playerActivity, streamId))
				gThread.start()

			if (requestType == RequestType.FINISHED) and (playerActivity == PlayerActivity.IDLE) and (self.playlist_last_item == streamId):
				gThread = threading.Thread(target=alexa_getnextitem, args=(self.navigation_token,))
				self.navigation_token = None
				gThread.start()

	def tunein_playlist(self, url):
		logger.debug("TUNE IN URL = %s", url)

		req = requests.get(url)
		lines = req.content.decode().split('\n')

		nurl = self.tunein_parser.parse_stream_url(lines[0])
		if nurl:
			return nurl[0]

		return ""


# Playback handler
def playback_callback(requestType, playerActivity, streamId):

	return player.playback_callback(requestType, playerActivity, streamId)

im = importlib.import_module('alexapi.playback_handlers.' + config['sound']['playback_handler'] + "handler", package=None)
cl = getattr(im, config['sound']['playback_handler'].capitalize() + 'Handler')
pHandler = cl(config, playback_callback)
player = Player(config, platform, pHandler)


path = os.path.realpath(__file__).rstrip(os.path.basename(__file__))
resources_path = os.path.join(path, 'resources', '')
tmp_path = os.path.join(tempfile.mkdtemp(prefix='AlexaPi-runtime-'), '')

MAX_VOLUME = 100
MIN_VOLUME = 30


def mrl_fix(url):
	if ('#' in url) and url.startswith('file://'):
		new_url = url.replace('#', '.hashMark.')
		os.rename(url.replace('file://', ''), new_url.replace('file://', ''))
		url = new_url

	return url


def internet_on():
	try:
		requests.get('https://api.amazon.com/auth/o2/token')
		logger.info("Connection OK")
		return True
	except requests.exceptions.RequestException:
		logger.error("Connection Failed")
		return False


class Token(object):

	_token = ''
	_timestamp = None
	_validity = 3570

	def __init__(self, aconfig):

		self._aconfig = aconfig

		if not self._aconfig.get('refresh_token'):
			logger.critical("AVS refresh_token not found in the configuration file. "
					"Run the setup again to fix your installation (see project wiki for installation instructions).")
			raise ConfigurationException

		self.renew()

	def __str__(self):

		if (not self._timestamp) or (time.time() - self._timestamp > self._validity):
			logger.debug("AVS token: Expired")
			self.renew()

		return self._token

	def renew(self):

		logger.info("AVS token: Requesting a new one")

		payload = {
			"client_id": self._aconfig['Client_ID'],
			"client_secret": self._aconfig['Client_Secret'],
			"refresh_token": self._aconfig['refresh_token'],
			"grant_type": "refresh_token"
		}

		url = "https://api.amazon.com/auth/o2/token"
		try:
			response = requests.post(url, data=payload)
			resp = json.loads(response.text)

			self._token = resp['access_token']
			self._timestamp = time.time()

			logger.info("AVS token: Obtained successfully")
		except requests.exceptions.RequestException as exp:
			logger.critical("AVS token: Failed to obtain a token: " + str(exp))


# from https://github.com/respeaker/Alexa/blob/master/alexa.py
def alexa_speech_recognizer_generate_data(audio, boundary):
	"""
	Generate a iterator for chunked transfer-encoding request of Alexa Voice Service
	Args:
		audio: raw 16 bit LSB audio data
		boundary: boundary of multipart content
	Returns:
	"""
	logger.debug('Start sending speech to Alexa Voice Service')
	chunk = '--%s\r\n' % boundary
	chunk += (
		'Content-Disposition: form-data; name="request"\r\n'
		'Content-Type: application/json; charset=UTF-8\r\n\r\n'
	)

	data = {
		"messageHeader": {
			"deviceContext": [{
				"name": "playbackState",
				"namespace": "AudioPlayer",
				"payload": {
					"streamId": "",
					"offsetInMilliseconds": "0",
					"playerActivity": "IDLE"
				}
			}]
		},
		"messageBody": {
			"profile": "alexa-close-talk",
			"locale": "en-us",
			"format": "audio/L16; rate=16000; channels=1"
		}
	}

	yield bytes(chunk + json.dumps(data) + '\r\n', 'utf8')

	chunk = '--%s\r\n' % boundary
	chunk += (
		'Content-Disposition: form-data; name="audio"\r\n'
		'Content-Type: audio/L16; rate=16000; channels=1\r\n\r\n'
	)

	yield bytes(chunk, 'utf8')

	for audio_chunk in audio:
		yield audio_chunk

	yield bytes('--%s--\r\n' % boundary, 'utf8')
	logger.debug('Finished sending speech to Alexa Voice Service')

	platform.indicate_processing()


def alexa_speech_recognizer(audio_stream):
	# https://developer.amazon.com/public/solutions/alexa/alexa-voice-service/rest/speechrecognizer-requests

	url = 'https://access-alexa-na.amazon.com/v1/avs/speechrecognizer/recognize'
	boundary = 'this-is-a-boundary'
	headers = {
		'Authorization': 'Bearer %s' % token,
		'Content-Type': 'multipart/form-data; boundary=%s' % boundary,
		'Transfer-Encoding': 'chunked',
	}

	data = alexa_speech_recognizer_generate_data(audio_stream, boundary)
	resp = requests.post(url, headers=headers, data=data)

	platform.indicate_processing(False)

	process_response(resp)


def alexa_getnextitem(navigationToken):
	# https://developer.amazon.com/public/solutions/alexa/alexa-voice-service/rest/audioplayer-getnextitem-request

	logger.debug("Sending GetNextItem Request...")

	url = 'https://access-alexa-na.amazon.com/v1/avs/audioplayer/getNextItem'
	headers = {
		'Authorization': 'Bearer %s' % token,
		'content-type': 'application/json; charset=UTF-8'
	}

	data = {
		"messageHeader": {},
		"messageBody": {
			"navigationToken": navigationToken
		}
	}

	response = requests.post(url, headers=headers, data=json.dumps(data))
	process_response(response)

def alexa_playback_progress_report_request(requestType, playerActivity, stream_id):
	# https://developer.amazon.com/public/solutions/alexa/alexa-voice-service/rest/audioplayer-events-requests
	# streamId                  Specifies the identifier for the current stream.
	# offsetInMilliseconds      Specifies the current position in the track, in milliseconds.
	# playerActivity            IDLE, PAUSED, or PLAYING

	logger.debug("Sending Playback Progress Report Request...")

	headers = {
		'Authorization': 'Bearer %s' % token
	}

	data = {
		"messageHeader": {},
		"messageBody": {
			"playbackState": {
				"streamId": stream_id,
				"offsetInMilliseconds": 0,
				"playerActivity": playerActivity.upper()
			}
		}
	}

	if requestType.upper() == RequestType.ERROR:
		# The Playback Error method sends a notification to AVS that the audio player has experienced an issue during playback.
		url = "https://access-alexa-na.amazon.com/v1/avs/audioplayer/playbackError"
	elif requestType.upper() == RequestType.FINISHED:
		# The Playback Finished method sends a notification to AVS that the audio player has completed playback.
		url = "https://access-alexa-na.amazon.com/v1/avs/audioplayer/playbackFinished"
	elif requestType.upper() == PlayerActivity.IDLE: # This is an error as described in https://github.com/alexa-pi/AlexaPi/issues/117
		# The Playback Idle method sends a notification to AVS that the audio player has reached the end of the playlist.
		url = "https://access-alexa-na.amazon.com/v1/avs/audioplayer/playbackIdle"
	elif requestType.upper() == RequestType.INTERRUPTED:
		# The Playback Interrupted method sends a notification to AVS that the audio player has been interrupted.
		# Note: The audio player may have been interrupted by a previous stop Directive.
		url = "https://access-alexa-na.amazon.com/v1/avs/audioplayer/playbackInterrupted"
	elif requestType.upper() == "PROGRESS_REPORT":
		# The Playback Progress Report method sends a notification to AVS with the current state of the audio player.
		url = "https://access-alexa-na.amazon.com/v1/avs/audioplayer/playbackProgressReport"
	elif requestType.upper() == RequestType.STARTED:
		# The Playback Started method sends a notification to AVS that the audio player has started playing.
		url = "https://access-alexa-na.amazon.com/v1/avs/audioplayer/playbackStarted"

	response = requests.post(url, headers=headers, data=json.dumps(data))
	if response.status_code != 204:
		logger.warning("(alexa_playback_progress_report_request Response) %s", response)
	else:
		logger.debug("Playback Progress Report was Successful")


def process_response(response):
	logger.debug("Processing Request Response...")

	if response.status_code == 200:
		try:
			data = bytes("Content-Type: ", 'utf-8') + bytes(response.headers['content-type'], 'utf-8') + bytes('\r\n\r\n', 'utf-8') + response.content
			msg = email.message_from_bytes(data) # pylint: disable=no-member
		except AttributeError:
			data = "Content-Type: " + response.headers['content-type'] + '\r\n\r\n' + response.content
			msg = email.message_from_string(data)

		for payload in msg.get_payload():
			if payload.get_content_type() == "application/json":
				j = json.loads(payload.get_payload())
				logger.debug("JSON String Returned: %s", json.dumps(j, indent=2))
			elif payload.get_content_type() == "audio/mpeg":
				filename = tmp_path + payload.get('Content-ID').strip("<>") + ".mp3"
				with open(filename, 'wb') as f:
					f.write(payload.get_payload(decode=True))
			else:
				logger.debug("NEW CONTENT TYPE RETURNED: %s", payload.get_content_type())

		# Now process the response
		if 'directives' in j['messageBody']:
			if not j['messageBody']['directives']:
				logger.debug("0 Directives received")

			for directive in j['messageBody']['directives']:
				if directive['namespace'] == 'SpeechSynthesizer':
					if directive['name'] == 'speak':
						player.play_speech(mrl_fix("file://" + tmp_path + directive['payload']['audioContent'].lstrip("cid:") + ".mp3"))

				elif directive['namespace'] == 'SpeechRecognizer':
					if directive['name'] == 'listen':
						logger.debug("Further Input Expected, timeout in: %sms", directive['payload']['timeoutIntervalInMillis'])

						player.play_speech(resources_path + 'beep.wav')
						timeout = directive['payload']['timeoutIntervalInMillis'] / 116
						audio_stream = capture.silence_listener(timeout)

						# now process the response
						alexa_speech_recognizer(audio_stream)

				elif directive['namespace'] == 'AudioPlayer':
					if directive['name'] == 'play':
						player.play_playlist(directive['payload'])

				elif directive['namespace'] == "Speaker":
					# speaker control such as volume
					if directive['name'] == 'SetVolume':
						vol_token = directive['payload']['volume']
						type_token = directive['payload']['adjustmentType']
						if (type_token == 'relative'):
							volume = player.get_volume() + int(vol_token)
						else:
							volume = int(vol_token)

						if (volume > MAX_VOLUME):
							volume = MAX_VOLUME
						elif (volume < MIN_VOLUME):
							volume = MIN_VOLUME

						player.set_volume(volume)

						logger.debug("new volume = %s", volume)

		# Additional Audio Iten
		elif 'audioItem' in j['messageBody']:
			player.play_playlist(j['messageBody'])

		return

	elif response.status_code == 204:
		logger.debug("Request Response is null (This is OKAY!)")
	else:
		logger.info("(process_response Error) Status Code: %s", response.status_code)
		response.connection.close()

		platform.indicate_failure()

trigger_thread = None
def trigger_callback(trigger):
	global trigger_thread

	triggers.disable()

	trigger_thread = threading.Thread(target=trigger_process, args=(trigger,))
	trigger_thread.setDaemon(True)
	trigger_thread.start()


def trigger_process(trigger):

	if player.is_playing():
		player.stop()

	# clean up the temp directory
	if not debug:
		for some_file in os.listdir(tmp_path):
			file_path = os.path.join(tmp_path, some_file)
			try:
				if os.path.isfile(file_path):
					os.remove(file_path)
			except Exception as exp: # pylint: disable=broad-except
				logger.warning(exp)

	if event_commands['pre_interaction']:
		subprocess.Popen(event_commands['pre_interaction'], shell=True, stdout=subprocess.PIPE)

	force_record = None
	if trigger.event_type in triggers.types_continuous:
		force_record = (trigger.continuous_callback, trigger.event_type in triggers.types_vad)

	if trigger.voice_confirm:
		player.play_speech(resources_path + 'alexayes.mp3')

	audio_stream = capture.silence_listener(force_record=force_record)
	alexa_speech_recognizer(audio_stream)

	triggers.enable()

	if event_commands['post_interaction']:
		subprocess.Popen(event_commands['post_interaction'], shell=True, stdout=subprocess.PIPE)


def cleanup(signal, frame):   # pylint: disable=redefined-outer-name,unused-argument
	platform.cleanup()
	pHandler.cleanup()
	shutil.rmtree(tmp_path)

	if event_commands['shutdown']:
		subprocess.Popen(event_commands['shutdown'], shell=True, stdout=subprocess.PIPE)

	sys.exit(0)


if __name__ == "__main__":

	for sig in (signal.SIGABRT, signal.SIGILL, signal.SIGINT, signal.SIGSEGV, signal.SIGTERM):
		signal.signal(sig, cleanup)

	if event_commands['startup']:
		subprocess.Popen(event_commands['startup'], shell=True, stdout=subprocess.PIPE)

	try:
		capture = alexapi.capture.Capture(config, tmp_path)
	except ConfigurationException as exp:
		logger.critical(exp)
		sys.exit(1)

	capture.setup(platform.indicate_recording)

	triggers.init(config, trigger_callback)
	triggers.setup()

	pHandler.setup()
	platform.setup()

	logger.info("Checking Internet Connection ...")
	while not internet_on():
		time.sleep(1)

	try:
		token = Token(config['alexa'])

		if not str(token):
			raise RuntimeError

	except (ConfigurationException, RuntimeError):
		platform.indicate_failure()
		sys.exit(1)

	platform_trigger_callback = triggers.triggers['platform'].platform_callback if 'platform' in triggers.triggers else None
	platform.after_setup(platform_trigger_callback)
	triggers.enable()

	if not silent:
		player.play_speech(resources_path + "hello.mp3")

	platform.indicate_success()

	while True:
		time.sleep(1)
