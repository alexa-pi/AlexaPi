from abc import ABCMeta, abstractmethod


class BaseTrigger:
	__metaclass__ = ABCMeta

	name = None
	type = None
	event_type = None
	voice_confirm = None

	_trigger_callback = None
	_config = None
	_tconfig = None

	def __init__(self, config, trigger_callback, trigger_name):

		self.name = trigger_name

		self._config = config
		self._tconfig = config['triggers'][trigger_name]
		self._trigger_callback = trigger_callback
		self.voice_confirm = self._tconfig['voice_confirm']

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
