from __future__ import print_function
import threading
import time
from collections import deque

import vlc

import alexapi.bcolors as bcolors
from basehandler import BaseHandler


class VlcHandler(BaseHandler):
	def __init__(self, config, callback_report):
		super(VlcHandler, self).__init__(config)

		self.__config = config
		self.__callback_report = callback_report

		self.vlc_instance = None
		self.player = None
		self.media_vlc_instance = None
		self.media_player = None

		self.event_manager = None

		self.queue = None
		self.processing_queue = False

		self.stream_id = None
		self.is_playing = None

		self.volume = None
		self.media_volume = None

		self.current_item_lock = threading.Event()

		# This has inverted logic
		self.play_lock = threading.Event()
		self.play_lock.set()

	def setup(self):

		parametersCommon = [
			# '--alsa-audio-device=mono'
			# '--file-logging'
			# '--logfile=vlc-log.txt'
		]

		parametersSpeech = parametersCommon

		if self.__config['sound']['output']:
			parametersSpeech.append('--aout=' + self.__config['sound']['output'])

			if self.__config['sound']['output_device']:
				parametersSpeech.append('--alsa-audio-device=' + self.__config['sound']['output_device'])

		self.vlc_instance = vlc.Instance(*parametersSpeech)
		self.player = self.vlc_instance.media_player_new()

		self.media_vlc_instance = self.vlc_instance
		self.media_player = self.player
		if self.__config['sound']['media_output']:
			parametersMedia = parametersCommon
			parametersMedia.append('--aout=' + self.__config['sound']['media_output'])

			if self.__config['sound']['media_output_device']:
				parametersMedia.append('--alsa-audio-device=' + self.__config['sound']['media_output_device'])

			self.media_vlc_instance = vlc.Instance(*parametersMedia)
			self.media_player = self.media_vlc_instance.media_player_new()

		if self.__config['sound']['default_volume']:
			self.volume = self.__config['sound']['default_volume']

		if self.__config['sound']['media_default_volume']:
			self.media_volume = self.__config['sound']['media_default_volume']

		self.queue = deque()

	def __play(self, item):

		if self.__config['debug']:
			print("{}Play_Audio Request for:{} {}".format(bcolors.OKBLUE, bcolors.ENDC, item['url']))

		if not self.play_lock.isSet():
			self.play_lock.wait()

		self.play_lock.clear()

		self.is_playing = True
		self.stream_id = item['streamId']

		vlcInstance = self.vlc_instance
		player = self.player
		if (item['audio_type'] == 'media'):
			vlcInstance = self.media_vlc_instance
			player = self.media_player

		media = vlcInstance.media_new(item['url'])
		player.set_media(media)

		volume = self.volume
		if (item['audio_type'] == 'media') and self.media_volume:
			volume = self.media_volume

		player.audio_set_volume(volume)

		self.event_manager = media.event_manager()
		self.event_manager.event_attach(vlc.EventType.MediaStateChanged, self.state_callback, player)

		player.play()
		if item['offset']:
			player.set_time(item['offset'])

		self.current_item_lock.wait()
		self.current_item_lock.clear()

		self.event_manager.event_detach(vlc.EventType.MediaStateChanged)
		self.player.stop()
		self.media_player.stop()

		self.is_playing = False
		self.play_lock.set()

	def queued_play(self, url, offset=0, audio_type='media', streamId=None):

		item = {
			'url': url,
			'offset': offset,
			'audio_type': audio_type,
			'streamId': streamId
		}

		self.queue.append(item)

		if not self.processing_queue:
			pqReady = threading.Event()
			pqThread = threading.Thread(target=self.process_queue, kwargs={'reportReady': pqReady})
			pqThread.start()

			pqReady.wait()

	def blocking_play(self, url, offset=0, audio_type='speech', streamId=None):

		item = {
			'url': url,
			'offset': offset,
			'audio_type': audio_type,
			'streamId': streamId
		}

		self.__play(item)

	def process_queue(self, reportReady=None):
		self.processing_queue = True

		if reportReady:
			reportReady.set()

		while len(self.queue):
			item = self.queue.popleft()
			self.__play(item)

			if len(self.queue) > 0:
				time.sleep(0.5)

		self.processing_queue = False

	def stop(self):
		self.queue.clear()

		self.player.stop()
		self.media_player.stop()

	def cleanup(self):
		self.stop()

	def set_volume(self, volume):
		self.volume = volume

	def set_media_volume(self, volume):
		self.media_volume = volume

	def state_callback(self, event, player): # pylint: disable=unused-argument

		state = player.get_state()

		if self.__config['debug']:
			print("{}Player State:{} {}".format(bcolors.OKGREEN, bcolors.ENDC, state))

		if state in [vlc.State.Playing, vlc.State.Stopped, vlc.State.Ended, vlc.State.Error]:

			report = {
				vlc.State.Playing: ("STARTED", "PLAYING", self.stream_id),
				vlc.State.Stopped: ("INTERRUPTED", "IDLE", self.stream_id),
				vlc.State.Ended: ("FINISHED", "IDLE", self.stream_id),
				vlc.State.Error: ("ERROR", "IDLE", self.stream_id)
			}

			rThread = threading.Thread(target=self.__callback_report, args=report[state])
			rThread.start()

			if state in [vlc.State.Stopped, vlc.State.Ended, vlc.State.Error]:

				self.stream_id = None
				self.current_item_lock.set()
