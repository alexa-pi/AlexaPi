from __future__ import print_function
import os
import sys

__fileNames = [
	os.path.join(os.path.realpath(__file__).rstrip(os.path.basename(__file__)), '..', 'config.yaml'),
	'/etc/opt/AlexaPi/config.yaml',
]

filename = ''
for fn in __fileNames:
	if os.path.isfile(fn):
		filename = fn
		break

if filename == '':
	print('ERROR: No configuration file found!')
	sys.exit(1)


def set_variable(variable, value):
	# WARNING: this is a silly implementation that doesn't care about YAML sections,
	# therefore a unique variable name is needed for now
	variable = variable[-1]

	lines = []
	with open(filename, 'r') as stream:
		for line in stream:
			strip = line.lstrip()
			if strip.startswith(variable):
				lines.append(line[0:line.find(strip)] + variable + ': "' + value + '"\n')
			else:
				lines.append(line)

	with open(filename, 'w') as stream:
		stream.writelines(lines)
