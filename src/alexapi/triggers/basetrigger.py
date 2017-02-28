from abc import ABCMeta, abstractmethod


class BaseTrigger:
	__metaclass__ = ABCMeta

	name = ''
	type = None
	event_type = None
	voice_confirm = None

	_trigger_callback = None
	_config = None
	_tconfig = None

	def __init__(self, config, trigger_callback):

		self._config = config
		self._tconfig = config['triggers'][self.name]
		self._trigger_callback = trigger_callback
		self.voice_confirm = self._tconfig['voice_confirm']

		self.validate_config()

	def validate_config(self):
		pass

	@abstractmethod
	def setup(self):
		pass

	@abstractmethod
	def run(self):
		pass

	@abstractmethod
	def enable(self):
		pass

	@abstractmethod
	def disable(self):
		pass

	def cleanup(self):
		pass
