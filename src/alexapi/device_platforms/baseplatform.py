from abc import ABCMeta, abstractmethod


class BasePlatform:
	__metaclass__ = ABCMeta

	def __init__(self, config, platform_name):
		self._config = config
		self._pconfig = config['platforms']['common']
		self._pconfig.update(config['platforms'][platform_name])

		self.should_confirm_trigger = self._pconfig['should_confirm_trigger']

		self.long_press_setup = False
		if ('long_press' in self._pconfig
			and 'command' in self._pconfig['long_press']
			and len(self._pconfig['long_press']['command']) > 0
			and 'duration' in self._pconfig['long_press']):
			self.long_press_setup = True



	@abstractmethod
	def setup(self):
		pass

	@abstractmethod
	def after_setup(self):
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
	def should_record(self):
		pass

	@abstractmethod
	def cleanup(self):
		pass
