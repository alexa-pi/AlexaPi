from abc import ABCMeta, abstractmethod


class BasePlatform:
	__metaclass__ = ABCMeta

	@abstractmethod
	def __init__(self, config):
		pass

	@abstractmethod
	def setup(self):
		pass

	@abstractmethod
	def after_setup(self):
		pass

	@abstractmethod
	def indicate_setup_failure(self):
		pass

	@abstractmethod
	def indicate_setup_success(self):
		pass

	@abstractmethod
	def indicate_recording(self, state=True):
		pass

	@abstractmethod
	def indicate_playback(self, state=True):
		pass

	@abstractmethod
	def should_record(self):
		pass

	@abstractmethod
	def cleanup(self):
		pass