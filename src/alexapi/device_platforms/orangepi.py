import time
import threading

from pyA20.gpio import gpio as GPIO

from rpilike import RPiLikePlatform


class OrangepiPlatform(RPiLikePlatform):

	def __init__(self, config):
		super(OrangepiPlatform, self).__init__(config, 'orangepi', GPIO)

	def setup(self):
		GPIO.init()
		GPIO.setcfg(self._pconfig['button'], GPIO.INPUT)
		GPIO.pullup(self._pconfig['button'], GPIO.PULLUP)
		GPIO.setcfg(self._pconfig['rec_light'], GPIO.OUTPUT)
		GPIO.setcfg(self._pconfig['plb_light'], GPIO.OUTPUT)

	def after_setup(self):
		# threaded detection of button press
		self.wait_for_button_thread()

	def wait_for_button_thread(self):
		thread = threading.Thread(target=self.wait_for_button, args=())
		thread.daemon = True
		thread.start()

	def wait_for_button(self):
		while True:
			if GPIO.input(self._pconfig['button']) == 0:
				self.detect_button()
			time.sleep(.1)

	def cleanup(self):
		GPIO.output(self._pconfig['rec_light'], GPIO.LOW)
		GPIO.output(self._pconfig['plb_light'], GPIO.LOW)
