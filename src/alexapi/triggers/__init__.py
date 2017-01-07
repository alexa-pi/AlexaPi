import importlib

triggers = {}


def init(config, trigger_callback):

	for name in config['triggers']:
		if config['triggers'][name]['enabled']:
			im = importlib.import_module('alexapi.triggers.' + name + 'trigger', package=None)
			cl = getattr(im, name.capitalize() + 'Trigger')

			triggers[name] = cl(config, trigger_callback)


def setup():
	for name in triggers:
		trigger = triggers[name]

		trigger.setup()
		trigger.run()


def enable(type_filter=None):
	for name in triggers:
		trigger = triggers[name]
		if (not type_filter) or (trigger.type == type_filter):
			trigger.enable()


def disable(type_filter=None):
	for name in triggers:
		trigger = triggers[name]
		if (not type_filter) or (trigger.type == type_filter):
			trigger.disable()


class TYPES(object):
	OTHER = 0
	VOICE = 1


class EVENT_TYPES(object): # pylint: disable=invalid-name
	ONESHOT_VAD = 1
	CONTINUOUS = 2
	CONTINUOUS_VAD = 3

types_vad = [
	EVENT_TYPES.ONESHOT_VAD,
	EVENT_TYPES.CONTINUOUS_VAD,
]

types_continuous = [
	EVENT_TYPES.CONTINUOUS,
	EVENT_TYPES.CONTINUOUS_VAD,
]
