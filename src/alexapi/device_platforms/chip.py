import CHIP_IO.GPIO as GPIO

from rpilike import RPiLikePlatform


class ChipPlatform(RPiLikePlatform):

	def __init__(self, config):
		super(ChipPlatform, self).__init__(config, 'chip', GPIO)

	def setup(self):
		GPIO.setwarnings(False)
		GPIO.cleanup()

		super(ChipPlatform, self).setup()
