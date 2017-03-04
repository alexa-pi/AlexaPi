import logging
import time

import alsaaudio
import webrtcvad

from .exceptions import ConfigurationException

logger = logging.getLogger(__name__)


class Capture(object):

	MAX_RECORDING_LENGTH = 8

	VAD_SAMPLERATE = 16000
	VAD_FRAME_MS = 30
	VAD_PERIOD = int((VAD_SAMPLERATE / 1000) * VAD_FRAME_MS)
	VAD_SILENCE_TIMEOUT = 1000
	VAD_THROWAWAY_FRAMES = 10

	_vad = None
	_config = None
	_tmp_path = None
	_state_callback = None

	def __init__(self, config, tmp_path):
		self._config = config
		self._tmp_path = tmp_path

		self.validate_config()

	def validate_config(self):
		input_device = self._config['sound']['input_device']
		input_devices = alsaaudio.pcms(alsaaudio.PCM_CAPTURE)

		if (input_device not in input_devices) and (not self._config['sound']['allow_unlisted_input_device']):
			raise ConfigurationException(
				"Your input_device '" + input_device + "' is invalid. Use one of the following:\n"
				+ '\n'.join(input_devices))

	def setup(self, state_callback):
		self._vad = webrtcvad.Vad(2)
		self._state_callback = state_callback

	def silence_listener(self, throwaway_frames=None, force_record=None):

		throwaway_frames = throwaway_frames or self.VAD_THROWAWAY_FRAMES

		logger.debug("Setting up recording")

		# Reenable reading microphone raw data
		inp = alsaaudio.PCM(alsaaudio.PCM_CAPTURE, alsaaudio.PCM_NORMAL, self._config['sound']['input_device'])
		inp.setchannels(1)
		inp.setrate(self.VAD_SAMPLERATE)
		inp.setformat(alsaaudio.PCM_FORMAT_S16_LE)
		inp.setperiodsize(self.VAD_PERIOD)

		debug = logging.getLogger('alexapi').getEffectiveLevel() == logging.DEBUG

		logger.debug("Start recording")

		if self._state_callback:
			self._state_callback()

		def _listen():
			start = time.time()

			do_VAD = True
			if force_record and not force_record[1]:
				do_VAD = False

			# Buffer as long as we haven't heard enough silence or the total size is within max size
			thresholdSilenceMet = False
			frames = 0
			numSilenceRuns = 0
			silenceRun = 0

			if debug:
				audio = b''

			if do_VAD:
				# do not count first 10 frames when doing VAD
				while frames < throwaway_frames:
					length, data = inp.read()
					frames += 1
					if length:
						yield data

						if debug:
							audio += data

			# now do VAD
			while (force_record and force_record[0]()) \
					or (do_VAD and (thresholdSilenceMet is False) and ((time.time() - start) < self.MAX_RECORDING_LENGTH)):

				length, data = inp.read()
				if length:
					yield data

					if debug:
						audio += data

					if do_VAD and (length == self.VAD_PERIOD):
						isSpeech = self._vad.is_speech(data, self.VAD_SAMPLERATE)

						if not isSpeech:
							silenceRun += 1
						else:
							silenceRun = 0
							numSilenceRuns += 1

				if do_VAD:
					# only count silence runs after the first one
					# (allow user to speak for total of max recording length if they haven't said anything yet)
					if (numSilenceRuns != 0) and ((silenceRun * self.VAD_FRAME_MS) > self.VAD_SILENCE_TIMEOUT):
						thresholdSilenceMet = True

			logger.debug("End recording")

			inp.close()

			if self._state_callback:
				self._state_callback(False)

			if debug:
				with open(self._tmp_path + 'recording.wav', 'wb') as rf:
					rf.write(audio)

		return _listen()
