#!/bin/bash

function install_device {
		run_pip install websocket-client
}

function install_device_config {
		config_set 'device' 'hyperion'
}