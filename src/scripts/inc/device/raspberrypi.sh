#!/bin/bash

# shellcheck disable=SC2034
DESCRIPTION="all Raspberry Pi variants"

function install_device {
    run_pip install RPi.GPIO

    local rulesFile="/etc/udev/rules.d/99-gpio.rules"

    grep "bcm2835-gpiomem" ${rulesFile} || cat >>${rulesFile} <<EOL
SUBSYSTEM=="bcm2835-gpiomem", KERNEL=="gpiomem", GROUP="gpio", MODE="0660"
EOL
}

function install_device_config {
    config_set 'input_device' 'plughw:CARD=Device,DEV=0'

    config_set 'device' 'raspberrypi'
}