#! /usr/bin/env python

from __future__ import print_function
import importlib
import os
import tempfile
import signal
import shutil
import time
import sys
import threading
import json
import optparse
import email

import yaml
import alsaaudio
import requests
from memcache import Client
import vlc

import tunein
import webrtcvad

from pocketsphinx import get_model_path
from pocketsphinx.pocketsphinx import Decoder
# from sphinxbase.sphinxbase import *

import alexapi.config
import alexapi.bcolors as bcolors

with open(alexapi.config.filename, 'r') as stream:
	config = yaml.load(stream)

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

cmdopts, cmdargs = parser.parse_args()
silent = cmdopts.silent
debug = cmdopts.debug

if 'debug' not in config:
	config['debug'] = debug

try:
	im = importlib.import_module('alexapi.device_platforms.' + config['platform']['device'], package=None)
	cl = getattr(im, config['platform']['device'].capitalize() + 'Platform')
	platform = cl(config)
except ImportError:
	from alexapi.device_platforms.desktop import DesktopPlatform
	platform = DesktopPlatform(config)

# Setup
recorded = False
servers = ["127.0.0.1:11211"]
mc = Client(servers, debug=1)
path = os.path.realpath(__file__).rstrip(os.path.basename(__file__))
resources_path = os.path.join(path, 'resources', '')
tmp_path = os.path.join(tempfile.mkdtemp(prefix='AlexaPi-runtime-'), '')

# PocketSphinx configuration
ps_config = Decoder.default_config()

# Set recognition model to US
ps_config.set_string('-hmm', os.path.join(get_model_path(), 'en-us'))
ps_config.set_string('-dict', os.path.join(get_model_path(), 'cmudict-en-us.dict'))

# Specify recognition key phrase
ps_config.set_string('-keyphrase', config['sphinx']['trigger_phrase'])
ps_config.set_float('-kws_threshold', 1e-5)

# Hide the VERY verbose logging information
if not debug:
	ps_config.set_string('-logfn', '/dev/null')

# Process audio chunk by chunk. On keyword detected perform action and restart search
decoder = Decoder(ps_config)
decoder.start_utt()

# Variables
player = None
nav_token = ""
streamurl = ""
streamid = ""
position = 0
audioplaying = False
tunein_parser = tunein.TuneIn(5000)
vad = webrtcvad.Vad(2)
currVolume = 100

# constants
VAD_SAMPLERATE = 16000
VAD_FRAME_MS = 30
VAD_PERIOD = (VAD_SAMPLERATE / 1000) * VAD_FRAME_MS
VAD_SILENCE_TIMEOUT = 1000
VAD_THROWAWAY_FRAMES = 10
MAX_RECORDING_LENGTH = 8
MAX_VOLUME = 100
MIN_VOLUME = 30


def internet_on():
	print("Checking Internet Connection...")
	try:
		requests.get('https://api.amazon.com/auth/o2/token')
		print("Connection {}OK{}".format(bcolors.OKGREEN, bcolors.ENDC))
		return True
	except:  # pylint: disable=bare-except
		print("Connection {}Failed{}".format(bcolors.WARNING, bcolors.ENDC))
		return False


def gettoken():
	token = mc.get("access_token")
	refresh = config['alexa']['refresh_token']
	if token:
		return token
	elif refresh:
		payload = {
			"client_id": config['alexa']['Client_ID'],
			"client_secret": config['alexa']['Client_Secret'],
			"refresh_token": refresh,
			"grant_type": "refresh_token"
		}
		url = "https://api.amazon.com/auth/o2/token"
		response = requests.post(url, data=payload)
		resp = json.loads(response.text)
		mc.set("access_token", resp['access_token'], 3570)
		return resp['access_token']
	else:
		return False


def alexa_speech_recognizer():
	# https://developer.amazon.com/public/solutions/alexa/alexa-voice-service/rest/speechrecognizer-requests
	if debug:
		print("{}Sending Speech Request...{}".format(bcolors.OKBLUE, bcolors.ENDC))
	# platform.indicate_playback()
	url = 'https://access-alexa-na.amazon.com/v1/avs/speechrecognizer/recognize'
	headers = {'Authorization': 'Bearer %s' % gettoken()}
	data = {
		"messageHeader": {
			"deviceContext": [
				{
					"name": "playbackState",
					"namespace": "AudioPlayer",
					"payload": {
						"streamId": "",
						"offsetInMilliseconds": "0",
						"playerActivity": "IDLE"
					}
				}
			]
		},
		"messageBody": {
			"profile": "alexa-close-talk",
			"locale": "en-us",
			"format": "audio/L16; rate=16000; channels=1"
		}
	}
	with open(tmp_path + 'recording.wav') as inf:
		files = [
			('file', ('request', json.dumps(data), 'application/json; charset=UTF-8')),
			('file', ('audio', inf, 'audio/L16; rate=16000; channels=1'))
		]
		resp = requests.post(url, headers=headers, files=files)

	process_response(resp)


def alexa_getnextitem(token):
	# https://developer.amazon.com/public/solutions/alexa/alexa-voice-service/rest/audioplayer-getnextitem-request
	time.sleep(0.5)
	if not audioplaying:
		if debug:
			print("{}Sending GetNextItem Request...{}".format(bcolors.OKBLUE, bcolors.ENDC))
		# platform.indicate_playback()
		url = 'https://access-alexa-na.amazon.com/v1/avs/audioplayer/getNextItem'
		headers = {
			'Authorization': 'Bearer %s' % gettoken(),
			'content-type': 'application/json; charset=UTF-8'}
		data = {
			"messageHeader": {},
			"messageBody": {
				"navigationToken": token
			}
		}
		response = requests.post(url, headers=headers, data=json.dumps(data))
		process_response(response)


def alexa_playback_progress_report_request(requestType, playerActivity, stream_id):
	# https://developer.amazon.com/public/solutions/alexa/alexa-voice-service/rest/audioplayer-events-requests
	# streamId                  Specifies the identifier for the current stream.
	# offsetInMilliseconds      Specifies the current position in the track, in milliseconds.
	# playerActivity            IDLE, PAUSED, or PLAYING
	if debug:
		print("{}Sending Playback Progress Report Request...{}".format(bcolors.OKBLUE, bcolors.ENDC))
	headers = {'Authorization': 'Bearer %s' % gettoken()}
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

	if requestType.upper() == "ERROR":
		# The Playback Error method sends a notification to AVS that the audio player has experienced an issue during playback.
		url = "https://access-alexa-na.amazon.com/v1/avs/audioplayer/playbackError"
	elif requestType.upper() == "FINISHED":
		# The Playback Finished method sends a notification to AVS that the audio player has completed playback.
		url = "https://access-alexa-na.amazon.com/v1/avs/audioplayer/playbackFinished"
	elif requestType.upper() == "IDLE":
		# The Playback Idle method sends a notification to AVS that the audio player has reached the end of the playlist.
		url = "https://access-alexa-na.amazon.com/v1/avs/audioplayer/playbackIdle"
	elif requestType.upper() == "INTERRUPTED":
		# The Playback Interrupted method sends a notification to AVS that the audio player has been interrupted.
		# Note: The audio player may have been interrupted by a previous stop Directive.
		url = "https://access-alexa-na.amazon.com/v1/avs/audioplayer/playbackInterrupted"
	elif requestType.upper() == "PROGRESS_REPORT":
		# The Playback Progress Report method sends a notification to AVS with the current state of the audio player.
		url = "https://access-alexa-na.amazon.com/v1/avs/audioplayer/playbackProgressReport"
	elif requestType.upper() == "STARTED":
		# The Playback Started method sends a notification to AVS that the audio player has started playing.
		url = "https://access-alexa-na.amazon.com/v1/avs/audioplayer/playbackStarted"

	response = requests.post(url, headers=headers, data=json.dumps(data))
	if response.status_code != 204:
		print("{}(alexa_playback_progress_report_request Response){} {}".format(bcolors.WARNING, bcolors.ENDC, response))
	else:
		if debug:
			print("{}Playback Progress Report was {}Successful!{}".format(bcolors.OKBLUE, bcolors.OKGREEN, bcolors.ENDC))


def process_response(resp):
	global nav_token, streamurl, streamid, currVolume
	if debug:
		print("{}Processing Request Response...{}".format(bcolors.OKBLUE, bcolors.ENDC))
	nav_token = ""
	streamurl = ""
	streamid = ""
	if resp.status_code == 200:
		data = "Content-Type: " + resp.headers['content-type'] + '\r\n\r\n' + resp.content
		msg = email.message_from_string(data)
		for payload in msg.get_payload():
			if payload.get_content_type() == "application/json":
				j = json.loads(payload.get_payload())
				if debug:
					print("{}JSON String Returned:{} {}".format(bcolors.OKBLUE, bcolors.ENDC, json.dumps(j)))
			elif payload.get_content_type() == "audio/mpeg":
				filename = tmp_path + payload.get('Content-ID').strip("<>") + ".mp3"
				with open(filename, 'wb') as f:
					f.write(payload.get_payload())
			else:
				if debug:
					print("{}NEW CONTENT TYPE RETURNED: {} {}".format(bcolors.WARNING, bcolors.ENDC, payload.get_content_type()))
		# Now process the response
		if 'directives' in j['messageBody']:
			if len(j['messageBody']['directives']) == 0:
				if debug:
					print("0 Directives received")
				platform.indicate_recording(False)
				platform.indicate_playback(False)

			for directive in j['messageBody']['directives']:
				if directive['namespace'] == 'SpeechSynthesizer':
					if directive['name'] == 'speak':
						platform.indicate_recording(False)
						play_audio("file://" + tmp_path + directive['payload']['audioContent'].lstrip("cid:") + ".mp3")
					for directive in j['messageBody']['directives']:  # if Alexa expects a response
						if directive['namespace'] == 'SpeechRecognizer':  # this is included in the same string as above if a response was expected
							if directive['name'] == 'listen':
								if debug:
									print("{}Further Input Expected, timeout in: {} {}ms".format(bcolors.OKBLUE, bcolors.ENDC, directive['payload']['timeoutIntervalInMillis']))
								play_audio(resources_path + 'beep.wav', 0, 100)
								timeout = directive['payload']['timeoutIntervalInMillis'] / 116
								# listen until the timeout from Alexa
								silence_listener(timeout)
								# now process the response
								alexa_speech_recognizer()
				elif directive['namespace'] == 'AudioPlayer':
					# do audio stuff - still need to honor the playBehavior
					if directive['name'] == 'play':
						nav_token = directive['payload']['navigationToken']
						for _stream in directive['payload']['audioItem']['streams']:
							if _stream['progressReportRequired']:
								streamid = _stream['streamId']
								# playBehavior = directive['payload']['playBehavior']
							if _stream['streamUrl'].startswith("cid:"):
								content = "file://" + tmp_path + _stream['streamUrl'].lstrip("cid:") + ".mp3"
							else:
								content = _stream['streamUrl']
							pThread = threading.Thread(target=play_audio, args=(content, _stream['offsetInMilliseconds']))
							pThread.start()
				elif directive['namespace'] == "Speaker":
					# speaker control such as volume
					if directive['name'] == 'SetVolume':
						vol_token = directive['payload']['volume']
						type_token = directive['payload']['adjustmentType']
						if type_token == 'relative':
							currVolume = currVolume + int(vol_token)
						else:
							currVolume = int(vol_token)

						if currVolume > MAX_VOLUME:
							currVolume = MAX_VOLUME
						elif currVolume < MIN_VOLUME:
							currVolume = MIN_VOLUME

						if debug:
							print("new volume = {}".format(currVolume))

		elif 'audioItem' in j['messageBody']: 			# Additional Audio Iten
			nav_token = j['messageBody']['navigationToken']
			for _stream in j['messageBody']['audioItem']['streams']:
				if _stream['progressReportRequired']:
					streamid = _stream['streamId']
				if _stream['streamUrl'].startswith("cid:"):
					content = "file://" + tmp_path + _stream['streamUrl'].lstrip("cid:") + ".mp3"
				else:
					content = _stream['streamUrl']
				pThread = threading.Thread(target=play_audio, args=(content, _stream['offsetInMilliseconds']))
				pThread.start()

		return
	elif resp.status_code == 204:
		platform.indicate_recording(False)
		for _ in range(0, 3):
			time.sleep(.2)
			platform.indicate_playback()
			time.sleep(.2)
			platform.indicate_playback(False)
		if debug:
			print("{}Request Response is null {}(This is OKAY!){}".format(bcolors.OKBLUE, bcolors.OKGREEN, bcolors.ENDC))
	else:
		print("{}(process_response Error){} Status Code: {}".format(bcolors.WARNING, bcolors.ENDC, resp.status_code))
		resp.connection.close()

		platform.indicate_playback(False)
		platform.indicate_recording(False)
		for _ in range(0, 3):
			time.sleep(.2)
			platform.indicate_recording()
			time.sleep(.2)
			platform.indicate_recording(False)


def play_audio(aud_file, offset=0, overRideVolume=0):   # pylint: disable=unused-argument
	if aud_file.find('radiotime.com') != -1:
		aud_file = tuneinplaylist(aud_file)
	global player, audioplaying
	if debug:
		print("{}Play_Audio Request for:{} {}".format(bcolors.OKBLUE, bcolors.ENDC, aud_file))
	platform.indicate_playback()

	parameters = [
		# '--alsa-audio-device=mono'
		# '--file-logging'
		# '--logfile=vlc-log.txt'
	]

	if config['sound']['output']:
		parameters.append('--aout=' + config['sound']['output'])

		if config['sound']['output_device']:
			parameters.append('--alsa-audio-device=' + config['sound']['output_device'])

	vlc_inst = vlc.Instance(*parameters)
	media = vlc_inst.media_new(aud_file)
	player = vlc_inst.media_player_new()
	player.set_media(media)
	mm = media.event_manager()
	mm.event_attach(vlc.EventType.MediaStateChanged, state_callback, player)
	audioplaying = True

	if overRideVolume == 0:
		player.audio_set_volume(currVolume)
	else:
		player.audio_set_volume(overRideVolume)

	player.play()
	while audioplaying:
		continue
	platform.indicate_playback(False)


def tuneinplaylist(url):
	if debug:
		print("TUNE IN URL = {}".format(url))
	req = requests.get(url)
	lines = req.content.split('\n')

	nurl = tunein_parser.parse_stream_url(lines[0])
	if len(nurl) != 0:
		return nurl[0]

	return ""


def state_callback(event, media_player):    # pylint: disable=unused-argument
	global nav_token, audioplaying, streamurl, streamid
	state = media_player.get_state()
	#  0: 'NothingSpecial'
	#  1: 'Opening'
	#  2: 'Buffering'
	#  3: 'Playing'
	#  4: 'Paused'
	#  5: 'Stopped'
	#  6: 'Ended'
	#  7: 'Error'
	if debug:
		print("{}Player State:{} {}".format(bcolors.OKGREEN, bcolors.ENDC, state))
	if state == 3:		# Playing
		if streamid != "":
			rThread = threading.Thread(target=alexa_playback_progress_report_request, args=("STARTED", "PLAYING", streamid))
			rThread.start()
	elif state == 5:  # Stopped
		audioplaying = False
		if streamid != "":
			rThread = threading.Thread(target=alexa_playback_progress_report_request, args=("INTERRUPTED", "IDLE", streamid))
			rThread.start()
		streamurl = ""
		streamid = ""
		nav_token = ""
	elif state == 6:  # Ended
		audioplaying = False
		if streamid != "":
			rThread = threading.Thread(target=alexa_playback_progress_report_request, args=("FINISHED", "IDLE", streamid))
			rThread.start()
			streamid = ""
		if streamurl != "":
			pThread = threading.Thread(target=play_audio, args=(streamurl,))
			streamurl = ""
			pThread.start()
		elif nav_token != "":
			gThread = threading.Thread(target=alexa_getnextitem, args=(nav_token,))
			gThread.start()
	elif state == 7:
		audioplaying = False
		if streamid != "":
			rThread = threading.Thread(target=alexa_playback_progress_report_request, args=("ERROR", "IDLE", streamid))
			rThread.start()
		streamurl = ""
		streamid = ""
		nav_token = ""


def silence_listener(throwaway_frames):
	# Reenable reading microphone raw data
	inp = alsaaudio.PCM(alsaaudio.PCM_CAPTURE, alsaaudio.PCM_NORMAL, config['sound']['input_device'])
	inp.setchannels(1)
	inp.setrate(VAD_SAMPLERATE)
	inp.setformat(alsaaudio.PCM_FORMAT_S16_LE)
	inp.setperiodsize(VAD_PERIOD)
	audio = ""

	# Buffer as long as we haven't heard enough silence or the total size is within max size
	thresholdSilenceMet = False
	frames = 0
	numSilenceRuns = 0
	silenceRun = 0
	start = time.time()

	platform.indicate_recording()

	# do not count first 10 frames when doing VAD
	while frames < throwaway_frames:  # VAD_THROWAWAY_FRAMES):
		length, data = inp.read()
		frames = frames + 1
		if length:
			audio += data

	# now do VAD
	while platform.should_record() or ((thresholdSilenceMet is False) and ((time.time() - start) < MAX_RECORDING_LENGTH)):
		length, data = inp.read()
		if length:
			audio += data

			if length == VAD_PERIOD:
				isSpeech = vad.is_speech(data, VAD_SAMPLERATE)

				if not isSpeech:
					silenceRun = silenceRun + 1
					# print "0"
				else:
					silenceRun = 0
					numSilenceRuns = numSilenceRuns + 1
					# print "1"

		# only count silence runs after the first one
		# (allow user to speak for total of max recording length if they haven't said anything yet)
		if (numSilenceRuns != 0) and ((silenceRun * VAD_FRAME_MS) > VAD_SILENCE_TIMEOUT):
			thresholdSilenceMet = True

	if debug:
		print ("Debug: End recording")

	# if debug: play_audio(resources_path+'beep.wav', 0, 100)

	platform.indicate_recording(False)
	with open(tmp_path + 'recording.wav', 'w') as rf:
		rf.write(audio)
	inp.close()


def loop():
	while True:
		record_audio = False

		# Enable reading microphone raw data
		inp = alsaaudio.PCM(alsaaudio.PCM_CAPTURE, alsaaudio.PCM_NORMAL, config['sound']['input_device'])
		inp.setchannels(1)
		inp.setrate(16000)
		inp.setformat(alsaaudio.PCM_FORMAT_S16_LE)
		inp.setperiodsize(1024)

		while not record_audio:
			time.sleep(.1)

			triggered = False
			# Process microphone audio via PocketSphinx, listening for trigger word
			while not triggered:
				# Read from microphone
				_, buf = inp.read()
				# Detect if keyword/trigger word was said
				decoder.process_raw(buf, False, False)

				triggered_by_platform = platform.should_record()
				triggered_by_voice = decoder.hyp() is not None
				triggered = triggered_by_platform or triggered_by_voice

			if audioplaying:
				player.stop()

			record_audio = True

			if triggered_by_voice or (triggered_by_platform and platform.should_confirm_trigger):
				play_audio(resources_path + 'alexayes.mp3', 0)

		# do the following things if either the button has been pressed or the trigger word has been said
		if debug:
			print ("detected the edge, setting up audio")

		# To avoid overflows close the microphone connection
		inp.close()

		# clean up the temp directory
		if not debug:
			for some_file in os.listdir(tmp_path):
				file_path = os.path.join(tmp_path, some_file)
				try:
					if os.path.isfile(file_path):
						os.remove(file_path)
				except Exception as exp:   # pylint: disable=broad-except
					print(exp)

		if debug:
			print("Starting to listen...")
		silence_listener(VAD_THROWAWAY_FRAMES)

		if debug:
			print("Debug: Sending audio to be processed")
		alexa_speech_recognizer()

		# Now that request is handled restart audio decoding
		decoder.end_utt()
		decoder.start_utt()


def setup():
	for sig in (signal.SIGABRT, signal.SIGILL, signal.SIGINT, signal.SIGSEGV, signal.SIGTERM):
		signal.signal(sig, cleanup)

	platform.setup()

	while not internet_on():
		print(".")

	token = gettoken()
	if not token:
		platform.indicate_setup_failure()

	platform.indicate_setup_success()

	if not silent:
		play_audio(resources_path + "hello.mp3")

	platform.after_setup()


def cleanup(signal, frame):   # pylint: disable=redefined-outer-name,unused-argument
	platform.cleanup()
	shutil.rmtree(tmp_path)
	sys.exit(0)


if __name__ == "__main__":
	setup()
	loop()
