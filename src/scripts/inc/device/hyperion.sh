#!/bin/bash

# shellcheck disable=SC2034
DESCRIPTION="Integrate with Hyperion Ambient Lightning Software"

function install_device {
		run_pip install websocket-client
}

function install_device_config {
		config_set 'device' 'hyperion'
}