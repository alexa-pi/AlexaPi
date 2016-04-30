#! /usr/bin/env python

import os
import random
import time
import RPi.GPIO as GPIO
import alsaaudio
import wave
import random
from creds import *
import requests
import json
import re
from memcache import Client
import vlc
import threading

#Settings
button = 18 		# GPIO Pin with button connected
plb_light = 24		# GPIO Pin for the playback/activity light
rec_light = 25		# GPIO Pin for the recording light
lights = [plb_light, rec_light] 	# GPIO Pins with LED's connected
device = "plughw:1" # Name of your microphone/sound card in arecord -L

#Setup
recorded = False
servers = ["127.0.0.1:11211"]
mc = Client(servers, debug=1)
path = os.path.realpath(__file__).rstrip(os.path.basename(__file__))

#Variables
p = ""
nav_token = ""
streamurl = ""
streamid = ""
position = 0
audioplaying = False

#Debug
debug = 1

class bcolors:
	HEADER = '\033[95m'
	OKBLUE = '\033[94m'
	OKGREEN = '\033[92m'
	WARNING = '\033[93m'
	FAIL = '\033[91m'
	ENDC = '\033[0m'
	BOLD = '\033[1m'
	UNDERLINE = '\033[4m'

def internet_on():
	print("Checking Internet Connection...")
	try:
		r =requests.get('https://api.amazon.com/auth/o2/token')
		print("Connection {}OK{}".format(bcolors.OKGREEN, bcolors.ENDC))
		return True
	except:
		print("Connection {}Failed{}".format(bcolors.WARNING, bcolors.ENDC))
		return False

def gettoken():
	token = mc.get("access_token")
	refresh = refresh_token
	if token:
		return token
	elif refresh:
		payload = {"client_id" : Client_ID, "client_secret" : Client_Secret, "refresh_token" : refresh, "grant_type" : "refresh_token", }
		url = "https://api.amazon.com/auth/o2/token"
		r = requests.post(url, data = payload)
		resp = json.loads(r.text)
		mc.set("access_token", resp['access_token'], 3570)
		return resp['access_token']
	else:
		return False

def alexa_speech_recognizer():
	# https://developer.amazon.com/public/solutions/alexa/alexa-voice-service/rest/speechrecognizer-requests
	if debug: print("{}Sending Speech Request...{}".format(bcolors.OKBLUE, bcolors.ENDC))
	GPIO.output(plb_light, GPIO.HIGH)
	url = 'https://access-alexa-na.amazon.com/v1/avs/speechrecognizer/recognize'
	headers = {'Authorization' : 'Bearer %s' % gettoken()}
	d = {
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
	with open(path+'recording.wav') as inf:
		files = [
				('file', ('request', json.dumps(d), 'application/json; charset=UTF-8')),
				('file', ('audio', inf, 'audio/L16; rate=16000; channels=1'))
				]
		r = requests.post(url, headers=headers, files=files)
	process_response(r)

def alexa_getnextitem(nav_token):
	# https://developer.amazon.com/public/solutions/alexa/alexa-voice-service/rest/audioplayer-getnextitem-request
	time.sleep(0.5)
        if audioplaying == False:
		if debug: print("{}Sending GetNextItem Request...{}".format(bcolors.OKBLUE, bcolors.ENDC))
		GPIO.output(plb_light, GPIO.HIGH)
		url = 'https://access-alexa-na.amazon.com/v1/avs/audioplayer/getNextItem'
		headers = {'Authorization' : 'Bearer %s' % gettoken(), 'content-type' : 'application/json; charset=UTF-8'}
		d = {
			"messageHeader": {},
			"messageBody": {
				"navigationToken": nav_token
			}
		}
		r = requests.post(url, headers=headers, data=json.dumps(d))
		process_response(r)
	
def alexa_playback_progress_report_request(requestType, playerActivity, streamid):
	# https://developer.amazon.com/public/solutions/alexa/alexa-voice-service/rest/audioplayer-events-requests
	# streamId                  Specifies the identifier for the current stream.
	# offsetInMilliseconds      Specifies the current position in the track, in milliseconds.
	# playerActivity            IDLE, PAUSED, or PLAYING
	if debug: print("{}Sending Playback Progress Report Request...{}".format(bcolors.OKBLUE, bcolors.ENDC))
	headers = {'Authorization' : 'Bearer %s' % gettoken()}
	d = {
		"messageHeader": {},
		"messageBody": {
			"playbackState": {
				"streamId": streamid,
				"offsetInMilliseconds": 0,
				"playerActivity": playerActivity.upper()
			}
		}
	}
	
	if requestType.upper() == "ERROR":
		# The Playback Error method sends a notification to AVS that the audio player has experienced an issue during playback.
		url = "https://access-alexa-na.amazon.com/v1/avs/audioplayer/playbackError"
	elif requestType.upper() ==  "FINISHED":
		# The Playback Finished method sends a notification to AVS that the audio player has completed playback.
		url = "https://access-alexa-na.amazon.com/v1/avs/audioplayer/playbackFinished"
	elif requestType.upper() ==  "IDLE":
		# The Playback Idle method sends a notification to AVS that the audio player has reached the end of the playlist.
		url = "https://access-alexa-na.amazon.com/v1/avs/audioplayer/playbackIdle"
	elif requestType.upper() ==  "INTERRUPTED":
		# The Playback Interrupted method sends a notification to AVS that the audio player has been interrupted. 
		# Note: The audio player may have been interrupted by a previous stop Directive.
		url = "https://access-alexa-na.amazon.com/v1/avs/audioplayer/playbackInterrupted"
	elif requestType.upper() ==  "PROGRESS_REPORT":
		# The Playback Progress Report method sends a notification to AVS with the current state of the audio player.
		url = "https://access-alexa-na.amazon.com/v1/avs/audioplayer/playbackProgressReport"
	elif requestType.upper() ==  "STARTED":
		# The Playback Started method sends a notification to AVS that the audio player has started playing.
		url = "https://access-alexa-na.amazon.com/v1/avs/audioplayer/playbackStarted"
	
	r = requests.post(url, headers=headers, data=json.dumps(d))
	if r.status_code != 204:
		print("{}(alexa_playback_progress_report_request Response){} {}".format(bcolors.WARNING, bcolors.ENDC, r))
	else:
		if debug: print("{}Playback Progress Report was {}Successful!{}".format(bcolors.OKBLUE, bcolors.OKGREEN, bcolors.ENDC))

def process_response(r):
	global nav_token, streamurl, streamid
	if debug: print("{}Processing Request Response...{}".format(bcolors.OKBLUE, bcolors.ENDC))
	nav_token = ""
	streamurl = ""
	streamid = ""
	if r.status_code == 200:
		for v in r.headers['content-type'].split(";"):
			if re.match('.*boundary.*', v):
				boundary = v.split("=")[1]
		data = r.content.split(boundary)
		n = re.search('(?=audio\/mpeg)(.*?)(?=\r\n)', r.content)
		r.connection.close()
		audio = ""
		for d in data:
			m = re.search('(?<=Content\-Type: )(.*?)(?=\r\n)', d)
			if m:
				c_type = m.group(0)
				if c_type == 'application/json':
					json_r = d.split('\r\n\r\n')[1].rstrip('\r\n--')
					if debug: print("{}JSON String Returned:{} {}".format(bcolors.OKBLUE, bcolors.ENDC, json_r))
					nav_token = json_string_value(json_r, "navigationToken")
					streamurl = json_string_value(json_r, "streamUrl")
					if json_r.find('"progressReportRequired":false') == -1:
						streamid = json_string_value(json_r, "streamId")
					if streamurl.find("cid:") == 0:					
						streamurl = ""
					playBehavior = json_string_value(json_r, "playBehavior")
					if n == None and streamurl != "" and streamid.find("cid:") == -1:
						pThread = threading.Thread(target=play_audio, args=(streamurl,))
						streamurl = ""
						pThread.start()
						return
					else:
						GPIO.output(lights, GPIO.LOW)
						for x in range(0, 3):
							time.sleep(.2)
							GPIO.output(rec_light, GPIO.HIGH)
							time.sleep(.2)
							GPIO.output(lights, GPIO.LOW)
				elif c_type == 'audio/mpeg':
					audio = d.split('\r\n\r\n')[1].rstrip('--')
					if audio != "":
						with open(path + "response.mp3", 'wb') as f:
							f.write(audio)
						GPIO.output(rec_light, GPIO.LOW)
						play_audio("response.mp3")
	elif r.status_code == 204:
		GPIO.output(rec_light, GPIO.LOW)
		for x in range(0, 3):
			time.sleep(.2)
			GPIO.output(plb_light, GPIO.HIGH)
			time.sleep(.2)
			GPIO.output(plb_light, GPIO.LOW)
		if debug: print("{}Request Response is null {}(This is OKAY!){}".format(bcolors.OKBLUE, bcolors.OKGREEN, bcolors.ENDC))
	else:
		print("{}(process_response Error){} Status Code: {}".format(bcolors.WARNING, bcolors.ENDC, r.status_code))
		r.connection.close()
		GPIO.output(lights, GPIO.LOW)
		for x in range(0, 3):
			time.sleep(.2)
			GPIO.output(rec_light, GPIO.HIGH)
			time.sleep(.2)
			GPIO.output(lights, GPIO.LOW)

def json_string_value(json_r, item):
	m = re.search('(?<={}":")(.*?)(?=")'.format(item), json_r)
	if m:
		if debug: print("{}{}:{} {}".format(bcolors.OKBLUE, item, bcolors.ENDC, m.group(0)))
		return m.group(0)
	else:
		return ""

def play_audio(file):
	global nav_token, p, audioplaying
	if debug: print("{}Play_Audio Request for:{} {}".format(bcolors.OKBLUE, bcolors.ENDC, file))
	GPIO.output(plb_light, GPIO.HIGH)
	#subprocess.Popen(['mpg123', '-q', '{}{}'.format(path, file)]).wait()	
	i = vlc.Instance('--aout=alsa', '--alsa-audio-device=hw:CARD=ALSA,DEV=0')
	mrl = ""
	if file == "response.mp3" or file == "hello.mp3":
		mrl = "{}{}".format(path, file)
	else:
		mrl = "{}".format(file)
	
	if mrl != "":
		m = i.media_new(mrl)
		p = i.media_player_new()
		p.set_media(m)
		mm = m.event_manager()
		#mm.event_attach(vlc.EventType.MediaPlayerTimeChanged, pos_callback)
		#mm.event_attach(vlc.EventType.MediaParsedChanged, meta_callback, m)
		mm.event_attach(vlc.EventType.MediaStateChanged, state_callback, p)
		audioplaying = True
		p.audio_set_volume(100)
		p.play()
		while audioplaying:
			continue
		GPIO.output(plb_light, GPIO.LOW)
	else:
		print("(play_audio) mrl = Nothing!")

def state_callback(event, player):
	global nav_token, audioplaying, streamurl, streamid
	state = player.get_state()
	#0: 'NothingSpecial'
	#1: 'Opening'
	#2: 'Buffering'
	#3: 'Playing'
	#4: 'Paused'
	#5: 'Stopped'
	#6: 'Ended'
	#7: 'Error'
	if debug: print("{}Player State:{} {}".format(bcolors.OKGREEN, bcolors.ENDC, state))
	if state == 3:		#Playing
		if streamid != "":
			rThread = threading.Thread(target=alexa_playback_progress_report_request, args=("STARTED", "PLAYING", streamid))
			rThread.start()
	elif state == 5:	#Stopped
		audioplaying = False
		if streamid != "":
			rThread = threading.Thread(target=alexa_playback_progress_report_request, args=("INTERRUPTED", "IDLE", streamid))
			rThread.start()
		streamurl = ""
		streamid = ""
		nav_token = ""
	elif state == 6:	#Ended
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
		

def meta_callback(event, media):
	title = media.get_meta(vlc.Meta.Title)
	artist = media.get_meta(vlc.Meta.Artist)
	album = media.get_meta(vlc.Meta.Album)
	tracknumber = media.get_meta(vlc.Meta.TrackNumber)
	url = media.get_meta(vlc.Meta.URL)
	nowplaying = media.get_meta(vlc.Meta.NowPlaying)
	print('{}Title:{} {}'.format(bcolors.OKBLUE, bcolors.ENDC, title))
	print('{}Artist:{} {}'.format(bcolors.OKBLUE, bcolors.ENDC, artist))
	print('{}Album:{} {}'.format(bcolors.OKBLUE, bcolors.ENDC, album))
	print('{}Track:{} {}'.format(bcolors.OKBLUE, bcolors.ENDC, tracknumber))
	print('{}Url:{} {}'.format(bcolors.OKBLUE, bcolors.ENDC, url))
	print('{}Now Playing:{} {}'.format(bcolors.OKBLUE, bcolors.ENDC, nowplaying))

def pos_callback(event):
	global position
	position = event.u.new_time
	if debug: print("{}Player Position:{} {}".format(bcolors.OKBLUE, bcolors.ENDC, format_time(position)))

def format_time(self, milliseconds):
	"""formats milliseconds to h:mm:ss
	"""
	self.position = milliseconds / 1000
	m, s = divmod(self.position, 60)
	h, m = divmod(m, 60)
	return "%d:%02d:%02d" % (h, m, s)

def start():
	global audioplaying, p
	while True:
		print("{}Ready to Record.{}".format(bcolors.OKBLUE, bcolors.ENDC))
		GPIO.wait_for_edge(button, GPIO.FALLING) # we wait for the button to be pressed
		if audioplaying: p.stop()
		print("{}Recording...{}".format(bcolors.OKBLUE, bcolors.ENDC))
		GPIO.output(rec_light, GPIO.HIGH)
		inp = alsaaudio.PCM(alsaaudio.PCM_CAPTURE, alsaaudio.PCM_NORMAL, device)
		inp.setchannels(1)
		inp.setrate(16000)
		inp.setformat(alsaaudio.PCM_FORMAT_S16_LE)
		inp.setperiodsize(500)
		audio = ""
		while(GPIO.input(button)==0): # we keep recording while the button is pressed
			l, data = inp.read()
			if l:
				audio += data
		print("{}Recording Finished.{}".format(bcolors.OKBLUE, bcolors.ENDC))
		rf = open(path+'recording.wav', 'w')
		rf.write(audio)
		rf.close()
		inp = None
		alexa_speech_recognizer()

if __name__ == "__main__":
	GPIO.setwarnings(False)
	GPIO.cleanup()
	GPIO.setmode(GPIO.BCM)
	GPIO.setup(button, GPIO.IN, pull_up_down=GPIO.PUD_UP)
	GPIO.setup(lights, GPIO.OUT)
	GPIO.output(lights, GPIO.LOW)
	while internet_on() == False:
		print(".")
	token = gettoken()
	if token == False:
		while True:
			for x in range(0, 5):
				time.sleep(.1)
				GPIO.output(rec_light, GPIO.HIGH)
				time.sleep(.1)
				GPIO.output(rec_light, GPIO.LOW)
	for x in range(0, 5):
		time.sleep(.1)
		GPIO.output(plb_light, GPIO.HIGH)
		time.sleep(.1)
		GPIO.output(plb_light, GPIO.LOW)
	play_audio("hello.mp3")
	start()
