import time
import threading
import logging
import sys

from .baseplatform import BasePlatform

logger = logging.getLogger(__name__)


class DesktopPlatform(BasePlatform):

	def __init__(self, config):
		super(DesktopPlatform, self).__init__(config, 'desktop')

		self.trigger_thread = None
		self.started = 0

	def setup(self):
		pass

	def indicate_failure(self):
		logger.info("setup_failure")

	def indicate_success(self):
		logger.info("setup_complete")

	def indicate_recording(self, state=True):
		logger.info("indicate_recording_on %s", state)

	def indicate_playback(self, state=True):
		logger.info("indicate_playback %s", state)

	def indicate_processing(self, state=True):
		logger.info("indicate_processing %s", state)

	def after_setup(self, trigger_callback=None):

		self._trigger_callback = trigger_callback

		if self._trigger_callback:
			self.trigger_thread = DesktopPlatformTriggerThread(self, trigger_callback)
			self.trigger_thread.setDaemon(True)
			self.trigger_thread.start()

	def force_recording(self):
		return time.time() - self.started < self._pconfig['min_seconds_to_record']

	def cleanup(self):
		self.trigger_thread.stop()


class DesktopPlatformTriggerThread(threading.Thread):
	def __init__(self, platform, trigger_callback):
		threading.Thread.__init__(self)

		self.platform = platform
		self._trigger_callback = trigger_callback
		self.should_run = True

	def stop(self):
		self.should_run = False

	def run(self):
		while self.should_run:
			key = ""
			while key != 'a':
				print('Type "a" to trigger Alexa: ')
				key = sys.stdin.readline().strip()

			self.platform.started = time.time()

			if self._trigger_callback:
				self._trigger_callback(self.platform.force_recording)
