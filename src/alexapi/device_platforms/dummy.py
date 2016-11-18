from __future__ import print_function

from baseplatform import BasePlatform


class DummyPlatform(BasePlatform):

	def __init__(self, config):
		super(DummyPlatform, self).__init__(config, 'dummy')

		self.should_confirm_trigger = False

	def setup(self):
		if self._pconfig['verbose']:
			print("setup")

	def indicate_failure(self):
		if self._pconfig['verbose']:
			print("setup_failure")

	def indicate_success(self):
		if self._pconfig['verbose']:
			print("setup_complete")

	def indicate_recording(self, state=True):
		if self._pconfig['verbose']:
			print("indicate_recording_on " + str(state))

	def indicate_playback(self, state=True):
		if self._pconfig['verbose']:
			print("indicate_playback " + str(state))

	def indicate_processing(self, state=True):
		if self._pconfig['verbose']:
			print("indicate_processing " + str(state))

	def after_setup(self):
		if self._pconfig['verbose']:
			print("after_setup")

	def should_record(self):
		return False

	def cleanup(self):
		if self._pconfig['verbose']:
			print("cleanup")
