# the library doesn't support python 3 actively (yet hopefully)
# pylint gives: Unable to import 'CHIP_IO.GPIO' (import-error)
import CHIP_IO.GPIO as GPIO # pylint: disable=import-error

from .rpilikeplatform import RPiLikePlatform


class ChipPlatform(RPiLikePlatform):

	def __init__(self, config):
		super(ChipPlatform, self).__init__(config, 'chip', GPIO)

	def setup(self):
		GPIO.setwarnings(False)
		GPIO.cleanup()

		super(ChipPlatform, self).setup()
