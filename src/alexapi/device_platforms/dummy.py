import sys

from baseplatform import BasePlatform


class DummyPlatform(BasePlatform):

	def __init__(self, config):
		super(DummyPlatform, self).__init__(config)

		self.__config = config
		self.__pconfig = config['platforms']['dummy']

		self.should_confirm_trigger = False

	def setup(self):
		if (self.__pconfig['verbose']): print("setup")

	def indicate_setup_failure(self):
		if (self.__pconfig['verbose']): print("setup_failure")
		sys.exit()

	def indicate_setup_success(self):
		if (self.__pconfig['verbose']): print("setup_complete")

	def indicate_recording(self, state=True):
		if (self.__pconfig['verbose']): print("indicate_recording_on " + str(state))

	def indicate_playback(self, state=True):
		if (self.__pconfig['verbose']): print("indicate_playback " + str(state))

	def after_setup(self):
		if (self.__pconfig['verbose']): print("after_setup")

	def should_record(self):
		return False

	def cleanup(self):
		if (self.__pconfig['verbose']): print("cleanup")