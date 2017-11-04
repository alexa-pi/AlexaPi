import threading
from abc import ABCMeta, abstractmethod

import alexapi.triggers as triggers
from .basetrigger import BaseTrigger


class VoiceTrigger(BaseTrigger):
	__metaclass__ = ABCMeta

	type = triggers.TYPES.VOICE

	_detector = None

	_enabled_lock = None
	_disabled_sync_lock = None

	def __init__(self, config, trigger_callback):

		super(VoiceTrigger, self).__init__(config, trigger_callback)

		self._enabled_lock = threading.Event()
		self._disabled_sync_lock = threading.Event()

	@abstractmethod
	def thread(self):
		pass

	def run(self):
		thread = threading.Thread(target=self.thread, args=())
		thread.setDaemon(True)
		thread.start()

	def enable(self):
		self._enabled_lock.set()
		self._disabled_sync_lock.clear()

	def disable(self):
		self._enabled_lock.clear()
		self._disabled_sync_lock.wait()
