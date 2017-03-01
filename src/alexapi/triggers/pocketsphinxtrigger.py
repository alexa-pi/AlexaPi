import os
import threading
import logging

import alsaaudio
from pocketsphinx import get_model_path
from pocketsphinx.pocketsphinx import Decoder

import alexapi.triggers as triggers
from .basetrigger import BaseTrigger

logger = logging.getLogger(__name__)


class PocketsphinxTrigger(BaseTrigger):

	type = triggers.TYPES.VOICE

	def __init__(self, config, trigger_callback):
		super(PocketsphinxTrigger, self).__init__(config, trigger_callback, 'pocketsphinx')

		self._enabled_lock = threading.Event()
		self._disabled_sync_lock = threading.Event()
		self._decoder = None

	def setup(self):
		# PocketSphinx configuration
		ps_config = Decoder.default_config()

		# Set recognition model to US
		ps_config.set_string('-hmm', os.path.join(get_model_path(), 'en-us'))
		ps_config.set_string('-dict', os.path.join(get_model_path(), 'cmudict-en-us.dict'))

		# Specify recognition key phrase
		ps_config.set_string('-keyphrase', self._tconfig['phrase'])
		ps_config.set_float('-kws_threshold', float(self._tconfig['threshold']))

		# Hide the VERY verbose logging information when not in debug
		if logging.getLogger('alexapi').getEffectiveLevel() != logging.DEBUG:
			ps_config.set_string('-logfn', '/dev/null')

		# Process audio chunk by chunk. On keyword detected perform action and restart search
		self._decoder = Decoder(ps_config)

	def run(self):
		thread = threading.Thread(target=self.thread, args=())
		thread.setDaemon(True)
		thread.start()

	def thread(self):
		while True:
			self._enabled_lock.wait()

			# Enable reading microphone raw data
			inp = alsaaudio.PCM(alsaaudio.PCM_CAPTURE, alsaaudio.PCM_NORMAL, self._config['sound']['input_device'])
			inp.setchannels(1)
			inp.setrate(16000)
			inp.setformat(alsaaudio.PCM_FORMAT_S16_LE)
			inp.setperiodsize(1024)

			self._decoder.start_utt()

			triggered = False
			while not triggered:

				if not self._enabled_lock.isSet():
					break

				# Read from microphone
				_, buf = inp.read()

				# Detect if keyword/trigger word was said
				self._decoder.process_raw(buf, False, False)

				triggered = self._decoder.hyp() is not None

			# To avoid overflows close the microphone connection
			inp.close()

			self._decoder.end_utt()

			self._disabled_sync_lock.set()

			if triggered:
				self._trigger_callback(self)

	def enable(self):
		self._enabled_lock.set()
		self._disabled_sync_lock.clear()

	def disable(self):
		self._enabled_lock.clear()
		self._disabled_sync_lock.wait()
