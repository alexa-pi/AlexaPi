import time
import os
import threading
import logging

import alexapi.triggers as triggers
from .basetrigger import BaseTrigger

logger = logging.getLogger(__name__)


class PlatformTrigger(BaseTrigger):

	type = triggers.TYPES.OTHER

	_platform_continuous_callback = None

	def __init__(self, config, trigger_callback):

		super(PlatformTrigger, self).__init__(config, trigger_callback, 'platform')

		event_types = {
			'oneshot-vad': triggers.EVENT_TYPES.ONESHOT_VAD,
			'continuous': triggers.EVENT_TYPES.CONTINUOUS,
			'continuous-vad': triggers.EVENT_TYPES.CONTINUOUS_VAD
		}

		self.event_type = event_types[self._tconfig['event_type']]

		self._enabled = False

		self.long_press_setup = False
		if (self.event_type in triggers.types_continuous
			and 'long_press' in self._tconfig
			and 'command' in self._tconfig['long_press']
			and self._tconfig['long_press']['command']
			and 'duration' in self._tconfig['long_press']):
			self.long_press_setup = True

	def setup(self):
		pass

	def run(self):
		pass

	def platform_callback(self, platform_continuous_callback=None):
		if self._enabled:
			self._platform_continuous_callback = platform_continuous_callback
			self._trigger_callback(self)

			if self._platform_continuous_callback and self.long_press_setup:
				long_press_thread = threading.Thread(target=self.long_press)
				long_press_thread.daemon = True
				long_press_thread.start()

	def continuous_callback(self):
		if not self._platform_continuous_callback:
			return False

		return self._platform_continuous_callback()

	def long_press(self):
		start_time = time.time()

		while self._platform_continuous_callback():
			if (time.time() - start_time > self._tconfig['long_press']['duration']):

				if ('audio_file' in self._tconfig['long_press']) and self._tconfig['long_press']['audio_file']:
					pass
					# play_audio(self._pconfig['long_press']['audio_file'].replace('{resources_path}', resources_path))

				logger.info("-- " + str(self._tconfig['long_press']['duration']) + " second button press detected. Running specified command.")

				os.system(self._tconfig['long_press']['command'])
				break

			time.sleep(.1)

	def enable(self):
		self._enabled = True

	def disable(self):
		self._enabled = False
