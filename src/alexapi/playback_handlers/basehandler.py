from abc import ABCMeta, abstractmethod


class BaseHandler:
	__metaclass__ = ABCMeta

	is_playing = False
	volume = None
	media_volume = None

	@abstractmethod
	def __init__(self, config):
		pass

	@abstractmethod
	def setup(self):
		pass

	@abstractmethod
	def queued_play(self, url, offset=0, audio_type='media', streamId=None):
		pass

	@abstractmethod
	def blocking_play(self, url, offset=0, audio_type='speech', streamId=None):
		pass

	@abstractmethod
	def stop(self):
		pass

	@abstractmethod
	def set_volume(self, volume):
		pass

	@abstractmethod
	def set_media_volume(self, volume):
		pass

	@abstractmethod
	def cleanup(self):
		pass
