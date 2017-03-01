#!/bin/bash

# shellcheck disable=SC2034
DESCRIPTION="an Arduino controled device for example; used for Teddy Ruxpin"

function install_device {
    run_pip install pyserial
}

function install_device_config {
    config_set 'device' 'serial'
}