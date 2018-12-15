import os
import logging
import time
import collections
import site

import pyaudio
from snowboy import snowboydetect  # pylint: disable=import-error

from .voicetrigger import VoiceTrigger
from ..capture import DeviceInfo
from ..exceptions import ConfigurationException

SNOWBOY_FOLDER = ''
try:
	for packages_path in site.getsitepackages():  # pylint: disable=no-member
		path_candidate = os.path.join(packages_path, 'snowboy')
		if os.path.exists(path_candidate):
			SNOWBOY_FOLDER = path_candidate
except AttributeError:
	SNOWBOY_FOLDER = os.path.dirname(snowboydetect.__file__)

logger = logging.getLogger(__name__)


# Copied from snowboy
class RingBuffer:
	"""Ring buffer to hold audio from PortAudio"""
	def __init__(self, size=4096):
		self._buf = collections.deque(maxlen=size)

	def extend(self, data):
		"""Adds data to the end of buffer"""
		self._buf.extend(data)

	def get(self):
		"""Retrieves data from the beginning of buffer and clears it"""
		tmp = bytes(bytearray(self._buf))
		self._buf.clear()
		return tmp


class SnowboyTrigger(VoiceTrigger):

	name = 'snowboy'

	_sleep_time = 0.03
	_ring_buffer = None

	_pa = None
	_device_info = None

	def __init__(self, config, trigger_callback, capture):  # pylint: disable=unused-argument
		super(SnowboyTrigger, self).__init__(config, trigger_callback)

		self._model = self._tconfig['model'].replace('{distribution}', os.path.join(SNOWBOY_FOLDER, 'resources'))
		self._sensitivity = self._tconfig['sensitivity']

		self._device_info = DeviceInfo()

	def validate_config(self):

		model_path = self._tconfig['model'].replace('{distribution}', os.path.join(SNOWBOY_FOLDER, 'resources'))
		if not os.path.isfile(model_path):
			raise ConfigurationException("Invalid snowboy model path: '" + model_path + "'")

	def setup(self):
		# """
		# :param decoder_model: decoder model file path, a string or a list of strings
		# :param resource: resource file path.
		# :param sensitivity: decoder sensitivity, a float of a list of floats.
		# 						  The bigger the value, the more senstive the
		# 						  decoder. If an empty list is provided, then the
		# 						  default sensitivity in the model will be used.
		# :param audio_gain: multiply input volume by this factor.
		# """

		audio_gain = 1

		tm = type(self._model)
		ts = type(self._sensitivity)
		if tm is not list:
			self._model = [self._model]
		if ts is not list:
			self._sensitivity = [self._sensitivity]
		model_str = ",".join(self._model)

		resource_filename = os.path.join(SNOWBOY_FOLDER, "resources/common.res")
		self._detector = snowboydetect.SnowboyDetect(resource_filename.encode(), model_str.encode())
		self._detector.SetAudioGain(audio_gain)
		num_hotwords = self._detector.NumHotwords()

		if len(self._model) > 1 and len(self._sensitivity) == 1:
			self._sensitivity = self._sensitivity * num_hotwords

		if self._sensitivity:
			assert num_hotwords == len(self._sensitivity), \
				"number of hotwords in self._model (%d) and sensitivity " \
				"(%d) does not match" % (num_hotwords, len(self._sensitivity))

			sensitivity_str = ",".join([str(t) for t in self._sensitivity])
			self._detector.SetSensitivity(sensitivity_str.encode())

		self._ring_buffer = RingBuffer(self._detector.NumChannels() * self._detector.SampleRate() * 5)

		self._pa = pyaudio.PyAudio()

	def _audio_callback(self, in_data, frame_count, time_info, status):  # pylint: disable=unused-argument
		self._ring_buffer.extend(in_data)
		play_data = chr(0) * len(in_data)

		return play_data, pyaudio.paContinue

	def thread(self):

		while True:
			self._enabled_lock.wait()

			stream_in = self._pa.open(
				input=True,
				input_device_index=self._device_info.get_device_index(self._config['sound']['input_device']),
				format=self._pa.get_format_from_width(self._detector.BitsPerSample() / 8),
				channels=self._detector.NumChannels(),
				rate=self._detector.SampleRate(),
				frames_per_buffer=2048,
				stream_callback=self._audio_callback)

			triggered = False
			while not triggered:
				if not self._enabled_lock.isSet():
					break

				data = self._ring_buffer.get()
				if not data:
					time.sleep(self._sleep_time)
					continue

				ans = self._detector.RunDetection(data)
				if ans == -1:
					logger.warning("Error initializing streams or reading audio data")
				elif ans > 0:
					triggered = True

			stream_in.stop_stream()
			stream_in.close()

			self._disabled_sync_lock.set()

			if triggered:
				self._trigger_callback(self)

	def cleanup(self):
		self.disable()
		self._pa.terminate()
