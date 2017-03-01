import logging
from .baseplatform import BasePlatform

logger = logging.getLogger(__name__)


class DummyPlatform(BasePlatform):

	def __init__(self, config):
		super(DummyPlatform, self).__init__(config, 'dummy')

	def setup(self):
		logger.debug("setup")

	def indicate_failure(self):
		logger.debug("setup_failure")

	def indicate_success(self):
		logger.debug("setup_complete")

	def indicate_recording(self, state=True):
		logger.debug("indicate_recording_on %s", state)

	def indicate_playback(self, state=True):
		logger.debug("indicate_playback %s", state)

	def indicate_processing(self, state=True):
		logger.debug("indicate_processing %s", state)

	def after_setup(self, trigger_callback=None): # pylint: disable=unused-argument
		logger.debug("after_setup")

	def force_recording(self):
		return False

	def cleanup(self):
		logger.debug("cleanup")
