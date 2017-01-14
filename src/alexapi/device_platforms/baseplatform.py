from abc import ABCMeta, abstractmethod


class BasePlatform:
	__metaclass__ = ABCMeta

	_trigger_callback = None

	def __init__(self, config, platform_name):
		self._config = config

		self._pconfig = {}
		if config['platforms']['common']:
			self._pconfig = config['platforms']['common']

		if config['platforms'][platform_name]:
			self._pconfig.update(config['platforms'][platform_name])

	@abstractmethod
	def setup(self):
		pass

	@abstractmethod
	def after_setup(self, trigger_callback=None):
		pass

	@abstractmethod
	def indicate_failure(self):
		pass

	@abstractmethod
	def indicate_success(self):
		pass

	@abstractmethod
	def indicate_recording(self, state=True):
		pass

	@abstractmethod
	def indicate_playback(self, state=True):
		pass

	@abstractmethod
	def indicate_processing(self, state=True):
		pass

	@abstractmethod
	def force_recording(self):
		pass

	@abstractmethod
	def cleanup(self):
		pass
