import logging
import time
import threading

import serial

from .baseplatform import BasePlatform

logger = logging.getLogger(__name__)


class SerialPlatform(BasePlatform):

	def __init__(self, config):
		super(SerialPlatform, self).__init__(config, 'serial')

		self.serial = None
		self.should_force_recording = False

	def setup(self):
		logging.debug("setup")

		self.serial = serial.Serial(self._pconfig.get('port', None), self._pconfig.get('baudrate', 9600))

	def indicate_failure(self):
		logging.debug("setup_failure")

		command = self._pconfig['messages']['failure']
		if command:
			self.serial.write(command)

	def indicate_success(self):
		logging.debug("setup_complete")

		command = self._pconfig['messages']['success']
		if command:
			self.serial.write(command)

	def indicate_recording(self, state=True):
		logging.debug("indicate_recording_on %s", state)

		command = self._pconfig['messages']['recording_' + ('start' if state else 'end')]
		if command:
			self.serial.write(command)

	def indicate_playback(self, state=True):
		logging.debug("indicate_playback %s", state)

		command = self._pconfig['messages']['playback_' + ('start' if state else 'end')]
		if command:
			self.serial.write(command)

	def indicate_processing(self, state=True):
		logging.debug("indicate_processing %s", state)

		command = self._pconfig['messages']['processing_' + ('start' if state else 'end')]
		if command:
			self.serial.write(command)

	def after_setup(self, trigger_callback=None):
		logging.debug("after_setup")

		self._trigger_callback = trigger_callback

		if self._trigger_callback:
			thread = threading.Thread(target=self.thread)
			thread.daemon = True
			thread.start()

	def force_recording(self):
		return self.should_force_recording

	def cleanup(self):
		logging.debug("cleanup")

		self.serial.close()

	def thread(self):
		while True:
			while self.serial.inWaiting():
				if self.serial.read() == self._pconfig['messages']['trigger']:
					self.should_force_recording = True

					self._trigger_callback(self.force_recording)
				else:
					self.should_force_recording = False

			time.sleep(0.1)
