from abc import ABCMeta, abstractmethod
import threading
import logging
import time
from collections import deque

from alexapi.constants import RequestType, PlayerActivity


logger = logging.getLogger(__name__)


class PlaybackAudioType(object):
	SPEECH = 'speech'
	MEDIA = 'media'

	def __init__(self):
		pass


class PlaybackItem(object):
	def __init__(self, url, offset, audio_type, stream_id):
		self.url = url
		self.offset = offset
		self.audio_type = audio_type
		self.stream_id = stream_id


class PlaybackLock(object):
	def __init__(self):
		# This has inverted logic
		self.play_lock = threading.Event()
		self.play_lock.set()
		self.is_playing = False

	def acquire(self):
		if not self.play_lock.isSet():
			self.play_lock.wait()
		self.play_lock.clear()
		self.is_playing = True

	def release(self):
		self.play_lock.set()
		self.is_playing = False


class BaseHandler(object):
	__metaclass__ = ABCMeta

	def __init__(self, config, callback_report):
		self.__config = config
		self.__callback_report = callback_report

		self.queue = None
		self.processing_queue = False

		self.queue = deque()
		self.processing_queue = False

		self.stream_id = None
		self.play_lock = PlaybackLock()

	@abstractmethod
	def on_setup(self):
		pass

	@abstractmethod
	def on_play(self, item):
		pass

	@abstractmethod
	def on_stop(self):
		pass

	@abstractmethod
	def on_cleanup(self):
		pass

	@abstractmethod
	def on_set_volume(self, volume):
		pass

	@abstractmethod
	def on_set_media_volume(self, volume):
		pass

	def report_play(self, debug_msg=''):
		logger.debug('Started play. %s', debug_msg)
		self.__callback_report(RequestType.STARTED, PlayerActivity.PLAYING, self.stream_id)

	def report_stop(self, debug_msg=''):
		logger.debug('Stopped play. %s', debug_msg)
		self.__callback_report(RequestType.INTERRUPTED, PlayerActivity.IDLE, self.stream_id)

	def report_finish(self, debug_msg=''):
		logger.debug('Finished play. %s', debug_msg)
		self.__callback_report(RequestType.FINISHED, PlayerActivity.IDLE, self.stream_id)

	def report_error(self, debug_msg=''):
		logger.debug('Error attempting play. %s', debug_msg)
		self.__callback_report(RequestType.ERROR, PlayerActivity.IDLE, self.stream_id)

	def setup(self):
		logger.debug('Setting up playback handler: %s', self.__class__.__name__)
		self.on_setup()

	def is_playing(self):
		return self.play_lock.is_playing

	def queued_play(self, url, offset=0, audio_type=PlaybackAudioType.MEDIA, stream_id=None):
		item = PlaybackItem(url, offset, audio_type, stream_id)
		self.queue.append(item)

		if not self.processing_queue:
			pqReady = threading.Event()
			pqThread = threading.Thread(target=self.__process_queue, kwargs={'reportReady': pqReady})
			pqThread.start()

			pqReady.wait()

	def blocking_play(self, url, offset=0, audio_type=PlaybackAudioType.SPEECH, stream_id=None):
		item = PlaybackItem(url, offset, audio_type, stream_id)
		self.__play(item)

	def stop(self):
		logger.debug('Stopping audio play')
		self.queue.clear()
		self.on_stop()
		self.play_lock.release()

	def cleanup(self):
		logger.debug('Cleaning up playback handler')
		self.on_cleanup()

	def set_volume(self, volume):
		logger.debug('Setting volume to: %s', volume)
		self.on_set_volume(volume)

	def set_media_volume(self, volume):
		logger.debug('Setting media volume to: %s', volume)
		self.on_set_media_volume(volume)

	def __play(self, item):
		logger.debug('Playing audio: %s', item.url)

		self.play_lock.acquire()
		self.stream_id = item.stream_id
		self.on_play(item)
		self.play_lock.release()

	def __process_queue(self, reportReady=None):
		self.processing_queue = True
		if reportReady:
			reportReady.set()

		while self.queue:
			item = self.queue.popleft()
			self.__play(item)
			if self.queue:
				time.sleep(0.5)

		self.processing_queue = False
