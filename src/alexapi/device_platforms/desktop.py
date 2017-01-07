from __future__ import print_function
import time
import threading

from baseplatform import BasePlatform


class DesktopPlatform(BasePlatform):

	def __init__(self, config):
		super(DesktopPlatform, self).__init__(config, 'desktop')

		self.trigger_thread = None
		self.started = 0

	def setup(self):
		pass

	def indicate_failure(self):
		print("setup_failure")

	def indicate_success(self):
		print("setup_complete")

	def indicate_recording(self, state=True):
		print("indicate_recording_on " + str(state))

	def indicate_playback(self, state=True):
		print("indicate_playback " + str(state))

	def indicate_processing(self, state=True):
		print("indicate_processing " + str(state))

	def after_setup(self, trigger_callback=None):

		self._trigger_callback = trigger_callback

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
				key = raw_input('Type "a" to trigger Alexa: ')

			self.platform.started = time.time()

			if self._trigger_callback:
				self._trigger_callback(self.platform.force_recording)
