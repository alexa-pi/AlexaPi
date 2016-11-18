import RPi.GPIO as GPIO

from rpilike import RPiLikePlatform


class RaspberrypiPlatform(RPiLikePlatform):

	def __init__(self, config):
		super(RaspberrypiPlatform, self).__init__(config, 'raspberrypi', GPIO)

	def setup(self):
		GPIO.setwarnings(False)
		GPIO.cleanup()
		GPIO.setmode(GPIO.BCM)

		super(RaspberrypiPlatform, self).setup()
