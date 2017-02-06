import subprocess
from .basehandler import BaseHandler, PlaybackAudioType

MAX_VOLUME_GAIN = 30


class SoxHandler(BaseHandler):
	def __init__(self, config, callback_report):
		super(SoxHandler, self).__init__(config, callback_report)
		self.__config = config

		self.volume_gain = 0
		self.media_volume_gain = 0

		self.parameters_speech = []
		self.parameters_media = []

		self.playback_padding = 0

		self.proc = None

	def on_setup(self):
		if self.__config['sound']['output']:
			self.parameters_speech.extend(['-t', self.__config['sound']['output']])
			if self.__config['sound']['output_device']:
				self.parameters_speech.append(self.__config['sound']['output_device'])

		if self.__config['sound']['media_output']:
			self.parameters_media.extend(['-t', self.__config['sound']['media_output']])
			if self.__config['sound']['media_output_device']:
				self.parameters_media.append(self.__config['sound']['media_output_device'])
		else:
			self.parameters_media = self.parameters_speech

		if self.__config['sound']['default_volume']:
			self.on_set_volume(self.__config['sound']['default_volume'])
		if self.__config['sound']['media_default_volume']:
			self.on_set_media_volume(self.__config['sound']['media_default_volume'])

		self.playback_padding = str(self.__config['sound']['playback_padding'])

	def on_play(self, item):
		# SoX can't play file URLs
		audio_file = item.url.replace('file://', '')

		sox_cmd = ['sox', '-q', audio_file]
		if item.audio_type == PlaybackAudioType.SPEECH:
			sox_cmd.extend(self.parameters_speech)
			sox_cmd.extend(['vol', str(self.volume_gain), 'dB'])
		else:
			sox_cmd.extend(self.parameters_media)
			sox_cmd.extend(['vol', str(self.media_volume_gain), 'dB'])

		if item.offset:
			sox_cmd.extend(['trim', self.__calculate_offset(item.offset)])

		sox_cmd.extend(['pad', self.playback_padding, self.playback_padding])

		self.report_play(' '.join(sox_cmd))
		play_err = u''
		try:
			self.proc = subprocess.Popen(sox_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
			_, stderr = self.proc.communicate()
			play_err = stderr.decode()
		except OSError as ex:
			play_err = str(ex).decode()

		if play_err:
			self.report_error(play_err)
		else:
			self.report_finish()

	def on_stop(self):
		stop_err = ''
		if self.proc:
			try:
				self.proc.kill()
			except OSError as ex:
				stop_err = str(ex)
		else:
			stop_err = 'No SoX process to stop'

		self.report_stop(stop_err)

	def on_cleanup(self):
		self.on_stop()

	def on_set_volume(self, volume):
		self.volume_gain = self.__calculate_volume_gain(volume)

	def on_set_media_volume(self, volume):
		self.media_volume_gain = self.__calculate_volume_gain(volume)

	@staticmethod
	def __calculate_volume_gain(volume):
		'''
		The volume is a percentage in AlexaPi configs. With SoX, volume is specified as a gain value.
		To change the volume the gain is specified as a value greater than or less than 0.
		'''
		return (MAX_VOLUME_GAIN * volume / 100) - MAX_VOLUME_GAIN

	@staticmethod
	def __calculate_offset(offset_in_milliseconds):
		hours = offset_in_milliseconds / (1000 * 60 * 60) % 24
		minutes_in_hour = offset_in_milliseconds / (1000 * 60) % 60
		seconds_in_minute = offset_in_milliseconds / 1000 % 60
		milliseconds_in_second = offset_in_milliseconds % 1000
		return '{}:{:0>2}:{:0>2}.{:0>3}'.format(hours, minutes_in_hour, seconds_in_minute, milliseconds_in_second)
