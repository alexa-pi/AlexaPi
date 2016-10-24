import time 
import os

import RPi.GPIO as GPIO

from baseplatform import BasePlatform
import alexapi.bcolors as bcolors


class RaspberrypiPlatform(BasePlatform):

	def __init__(self, config):
		super(RaspberrypiPlatform, self).__init__(config)

		self.__config = config
		self.__pconfig = config['platforms']['common']
		self.__pconfig.update(config['platforms']['raspberrypi'])

		self.__pconfig['lights'] = [self.__pconfig['rec_light'], self.__pconfig['plb_light']]

		self.long_press_setup = False
		if ('long_press' in self.__pconfig
				and 'command' in self.__pconfig['long_press']
				and len(self.__pconfig['long_press']['command']) > 0
				and 'duration' in self.__pconfig['long_press']):

			self.long_press_setup = True

		self.should_confirm_trigger = self.__pconfig['should_confirm_trigger']

		self.button_pressed = False

	def setup(self):
		GPIO.setwarnings(False)
		GPIO.cleanup()
		GPIO.setmode(GPIO.BCM)
		GPIO.setup(self.__pconfig['button'], GPIO.IN, pull_up_down=GPIO.PUD_UP)
		GPIO.setup(self.__pconfig['lights'], GPIO.OUT)
		GPIO.output(self.__pconfig['lights'], GPIO.LOW)

	def indicate_setup_failure(self):
		while True:
			for x in range(0, 5):
				time.sleep(.1)
				GPIO.output(self.__pconfig['rec_light'], GPIO.HIGH)
				time.sleep(.1)
				GPIO.output(self.__pconfig['rec_light'], GPIO.LOW)

	def indicate_setup_success(self):
		for x in range(0, 5):
			time.sleep(.1)
			GPIO.output(self.__pconfig['plb_light'], GPIO.HIGH)
			time.sleep(.1)
			GPIO.output(self.__pconfig['plb_light'], GPIO.LOW)

	def after_setup(self):
		# threaded detection of button press
		GPIO.add_event_detect(self.__pconfig['button'], GPIO.FALLING, callback=self.detect_button, bouncetime=100)

	def indicate_recording(self, state=True):
		GPIO.output(self.__pconfig['rec_light'], GPIO.HIGH if state == True else GPIO.LOW)

	def indicate_playback(self, state=True):
		GPIO.output(self.__pconfig['plb_light'], GPIO.HIGH if state == True else GPIO.LOW)

	def detect_button(self, channel):
		buttonPress = time.time()
		self.button_pressed = True

		if self.__config['debug']: print("{}Button Pressed! Recording...{}".format(bcolors.OKBLUE, bcolors.ENDC))

		time.sleep(.5)  # time for the button input to settle down
		while (GPIO.input(self.__pconfig['button']) == 0):
			time.sleep(.1)

			if (self.long_press_setup) and (time.time() - buttonPress > self.__pconfig['long_press']['duration']):

				if ('audio_file' in self.__pconfig['long_press']) and (len(self.__pconfig['long_press']['audio_file']) > 0):
					pass
					# play_audio(self.__pconfig['long_press']['audio_file'].replace('{resources_path}', resources_path))

				if self.__config['debug']:
					print(("{} -- " + str(self.__pconfig['long_press']['duration']) + " second button press detected. Running specified command. -- {}").format(bcolors.WARNING, bcolors.ENDC))

				os.system(self.__pconfig['long_press']['command'])

		if self.__config['debug']: print("{}Recording Finished.{}".format(bcolors.OKBLUE, bcolors.ENDC))

		self.button_pressed = False

		time.sleep(.5)  # more time for the button to settle down

	# def wait_for_trigger(self):
	# 	# we wait for the button to be pressed
	# 	GPIO.wait_for_edge(self.__pconfig['button'], GPIO.FALLING)

	def should_record(self):
		return self.button_pressed

	def cleanup(self):
		GPIO.remove_event_detect(self.__pconfig['button'])

		GPIO.output(self.__pconfig['rec_light'], GPIO.LOW)
		GPIO.output(self.__pconfig['plb_light'], GPIO.LOW)