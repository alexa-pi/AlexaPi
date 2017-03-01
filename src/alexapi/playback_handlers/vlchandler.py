import threading
import logging
import vlc
from .basehandler import BaseHandler, PlaybackAudioType


logger = logging.getLogger(__name__)


class VlcHandler(BaseHandler):
	def __init__(self, config, callback_report):
		super(VlcHandler, self).__init__(config, callback_report)

		self.__config = config

		self.vlc_instance = None
		self.player = None
		self.media_vlc_instance = None
		self.media_player = None

		self.event_manager = None

		self.volume = None
		self.media_volume = None

		self.current_item_lock = threading.Event()

	def on_setup(self):

		parametersCommon = [
			# '--alsa-audio-device=mono'
			# '--file-logger'
			# '--logfile=vlc-log.txt'
		]

		parametersSpeech = parametersCommon

		if self.__config['sound']['output']:
			parametersSpeech.append('--aout=' + self.__config['sound']['output'])

			if self.__config['sound']['output_device']:
				parametersSpeech.append('--alsa-audio-device=' + self.__config['sound']['output_device'])

		self.vlc_instance = vlc.Instance(*parametersSpeech)
		self.player = self.vlc_instance.media_player_new()

		self.media_vlc_instance = self.vlc_instance
		self.media_player = self.player
		if self.__config['sound']['media_output']:
			parametersMedia = parametersCommon
			parametersMedia.append('--aout=' + self.__config['sound']['media_output'])

			if self.__config['sound']['media_output_device']:
				parametersMedia.append('--alsa-audio-device=' + self.__config['sound']['media_output_device'])

			self.media_vlc_instance = vlc.Instance(*parametersMedia)
			self.media_player = self.media_vlc_instance.media_player_new()

		if self.__config['sound']['default_volume']:
			self.volume = self.__config['sound']['default_volume']

		if self.__config['sound']['media_default_volume']:
			self.media_volume = self.__config['sound']['media_default_volume']

	def on_play(self, item):
		vlcInstance = self.vlc_instance
		player = self.player
		if (item.audio_type == PlaybackAudioType.MEDIA):
			vlcInstance = self.media_vlc_instance
			player = self.media_player

		media = vlcInstance.media_new(item.url)
		player.set_media(media)

		volume = self.volume
		if (item.audio_type == PlaybackAudioType.MEDIA) and self.media_volume:
			volume = self.media_volume

		player.audio_set_volume(volume)

		self.event_manager = media.event_manager()
		self.event_manager.event_attach(vlc.EventType.MediaStateChanged, self.state_callback, player)

		player.play()
		if item.offset:
			player.set_time(item.offset)

		self.current_item_lock.wait()
		self.current_item_lock.clear()

		self.event_manager.event_detach(vlc.EventType.MediaStateChanged)
		self.player.stop()
		self.media_player.stop()

	def on_stop(self):
		self.player.stop()
		self.media_player.stop()

	def on_cleanup(self):
		self.on_stop()

	def on_set_volume(self, volume):
		self.volume = volume

	def on_set_media_volume(self, volume):
		self.media_volume = volume

	def state_callback(self, event, player): # pylint: disable=unused-argument

		state = player.get_state()

		logger.debug("Player State: %s", state)

		if state in [vlc.State.Playing, vlc.State.Stopped, vlc.State.Ended, vlc.State.Error]:

			report = {
				vlc.State.Playing: self.report_play,
				vlc.State.Stopped: self.report_stop,
				vlc.State.Ended: self.report_finish,
				vlc.State.Error: self.report_error
			}

			report[state]()

			if state in [vlc.State.Stopped, vlc.State.Ended, vlc.State.Error]:
				self.current_item_lock.set()
