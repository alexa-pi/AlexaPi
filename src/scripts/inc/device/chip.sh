#!/bin/bash

# shellcheck disable=SC2034
DESCRIPTION="C.H.I.P."

function install_device {
    run_pip install git+https://github.com/xtacocorex/CHIP_IO.git
}

function install_device_config {
    config_set 'output_device' 'plughw:1'
    config_set 'playback_padding' '1'

    handle_root_platform 'chip'
}