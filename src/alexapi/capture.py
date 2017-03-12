import logging
import time
import threading
import os
import queue

import webrtcvad

from .exceptions import ConfigurationException

os.environ["PA_ALSA_PLUGHW"] = "1"
import pyaudio # pylint: disable=wrong-import-position,wrong-import-order


logger = logging.getLogger(__name__)


class DeviceInfo(object):

	_pa = None

	def __init__(self):
		self._pa = pyaudio.PyAudio()

	def get_device_list(self, input_only=False):

		device_list = []
		for i in range(self._pa.get_device_count()):
			if (not input_only) or (input_only and self._pa.get_device_info_by_index(i)['maxInputChannels'] > 0):
				device_list.append(self._pa.get_device_info_by_index(i)['name'])

		return device_list

	def get_device_index(self, name):
		if not name:
			return None

		return self.get_device_list().index(name)

	def __del__(self):
		self._pa.terminate()


class Capture(object):

	MAX_RECORDING_LENGTH = 8

	VAD_SAMPLERATE = 16000
	VAD_FRAME_MS = 30
	VAD_PERIOD = int((VAD_SAMPLERATE / 1000) * VAD_FRAME_MS)
	VAD_SILENCE_TIMEOUT = 1000
	VAD_THROWAWAY_FRAMES = 10

	_pa = None
	_pa_exception_on_overflow = False

	_handle = None
	_handle_chunk_size = None

	_device_info = None
	_stream = None
	_callback_data = None
	_queue = None
	_vad = None
	_config = None
	_tmp_path = None
	_state_callback = None
	_interrupt = False
	_recording_lock_inverted = None

	def __init__(self, config, tmp_path):
		self._config = config
		self._tmp_path = tmp_path

		self._pa = pyaudio.PyAudio()
		self._queue = queue.Queue()
		self._device_info = DeviceInfo()

		self._recording_lock_inverted = threading.Event()
		self._recording_lock_inverted.set()

		self.validate_config()

	def validate_config(self):
		input_device = self._config['sound']['input_device']
		input_devices = self._device_info.get_device_list(True)

		if input_device and (input_device not in input_devices):
			raise ConfigurationException(
				"Your input_device '" + input_device + "' is invalid. Use one of the following:\n"
				+ '\n'.join(input_devices))

	def setup(self, state_callback):
		self._vad = webrtcvad.Vad(2)
		self._state_callback = state_callback

	def cleanup(self):

		if not self._recording_lock_inverted.isSet():
			self._interrupt = True
			self._recording_lock_inverted.wait()

		self._pa.terminate()

	def handle_init(self, rate, chunk_size):

		self._handle = self._pa.open(
			input=True,
			input_device_index=self._device_info.get_device_index(self._config['sound']['input_device']),
			format=pyaudio.paInt16,
			channels=1,
			rate=rate,
			frames_per_buffer=chunk_size
		)

		self._handle_chunk_size = chunk_size

	def handle_read(self):
		return self._handle.read(self._handle_chunk_size, exception_on_overflow=self._pa_exception_on_overflow)

	def handle_release(self):
		self._handle.close()

	def _callback(self, in_data, frame_count, time_info, status):  # pylint: disable=unused-argument

		debug = logging.getLogger('alexapi').getEffectiveLevel() == logging.DEBUG

		if not in_data:
			self._queue.put(False)
			return None, pyaudio.paAbort

		do_VAD = True
		if self._callback_data['force_record'] and not self._callback_data['force_record'][1]:
			do_VAD = False

		# do not count first 10 frames when doing VAD
		if do_VAD and (self._callback_data['frames'] < self._callback_data['throwaway_frames']):
			self._callback_data['frames'] += 1

		# now do VAD
		elif (self._callback_data['force_record'] and self._callback_data['force_record'][0]()) \
				or (do_VAD and (self._callback_data['thresholdSilenceMet'] is False)
					and ((time.time() - self._callback_data['start']) < self.MAX_RECORDING_LENGTH)):

			if do_VAD:

				if int(len(in_data) / 2) == self.VAD_PERIOD:
					isSpeech = self._vad.is_speech(in_data, self.VAD_SAMPLERATE)

					if not isSpeech:
						self._callback_data['silenceRun'] += 1
					else:
						self._callback_data['silenceRun'] = 0
						self._callback_data['numSilenceRuns'] += 1

				# only count silence runs after the first one
				# (allow user to speak for total of max recording length if they haven't said anything yet)
				if (self._callback_data['numSilenceRuns'] != 0) \
						and ((self._callback_data['silenceRun'] * self.VAD_FRAME_MS) > self.VAD_SILENCE_TIMEOUT):
					self._callback_data['thresholdSilenceMet'] = True

		else:
			self._queue.put(False)
			return None, pyaudio.paComplete

		self._queue.put(in_data)
		if debug:
			self._callback_data['audio'] += in_data

		return None, pyaudio.paContinue

	def silence_listener(self, throwaway_frames=None, force_record=None):

		logger.debug("Recording: Setting up")

		self._recording_lock_inverted.clear()

		debug = logging.getLogger('alexapi').getEffectiveLevel() == logging.DEBUG

		if self._state_callback:
			self._state_callback()

		self._queue.queue.clear()

		self._callback_data = {
			'start': time.time(),
			'thresholdSilenceMet': False,  # Buffer as long as we haven't heard enough silence or the total size is within max size
			'frames': 0,
			'throwaway_frames': throwaway_frames or self.VAD_THROWAWAY_FRAMES,
			'numSilenceRuns': 0,
			'silenceRun': 0,
			'force_record': force_record,
			'audio': b'' if debug else False,
		}

		stream = self._pa.open(
			input=True,
			input_device_index=self._device_info.get_device_index(self._config['sound']['input_device']),
			format=pyaudio.paInt16,
			channels=1,
			rate=self.VAD_SAMPLERATE,
			frames_per_buffer=self.VAD_PERIOD,
			stream_callback=self._callback,
			start=False
		)

		logger.debug("Recording: Start")
		stream.start_stream()

		def _listen():
			while True:
				try:
					data = self._queue.get(block=True, timeout=2)
					if not data or self._interrupt:
						break

					yield data
				except queue.Empty:
					break

			stream.stop_stream()
			logger.debug("Recording: End")
			stream.close()

			if self._state_callback:
				self._state_callback(False)

			if debug:
				with open(self._tmp_path + 'recording.wav', 'wb') as rf:
					rf.write(self._callback_data['audio'])

			self._recording_lock_inverted.set()

		return _listen()
