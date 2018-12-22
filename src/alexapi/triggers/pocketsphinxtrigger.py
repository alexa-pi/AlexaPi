import os
import threading
import logging
import platform

from pocketsphinx import get_model_path
from pocketsphinx.pocketsphinx import Decoder

from .voicetrigger import VoiceTrigger

logger = logging.getLogger(__name__)


class PocketsphinxTrigger(VoiceTrigger):

	name = 'pocketsphinx'

	AUDIO_CHUNK_SIZE = 1024
	AUDIO_RATE = 16000

	_capture = None

	def __init__(self, config, trigger_callback, capture):
		super(PocketsphinxTrigger, self).__init__(config, trigger_callback)

		self._capture = capture

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

			null_path = '/dev/null'
			if platform.system() == 'Windows':
				null_path = 'nul'

			ps_config.set_string('-logfn', null_path)

		# Process audio chunk by chunk. On keyword detected perform action and restart search
		self._detector = Decoder(ps_config)

	def thread(self):
		while True:
			self._enabled_lock.wait()

			self._capture.handle_init(self.AUDIO_RATE, self.AUDIO_CHUNK_SIZE)

			self._detector.start_utt()

			triggered = False
			while not triggered:

				if not self._enabled_lock.isSet():
					break

				# Read from microphone
				data = self._capture.handle_read()

				# Detect if keyword/trigger word was said
				self._detector.process_raw(data, False, False)

				triggered = self._detector.hyp() is not None

			self._capture.handle_release()

			self._detector.end_utt()

			self._disabled_sync_lock.set()

			if triggered:
				self._trigger_callback(self)
