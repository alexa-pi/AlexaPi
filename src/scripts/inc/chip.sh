#!/bin/bash

function install_device {
    run_pip install git+https://github.com/xtacocorex/CHIP_IO.git
}

function install_device_config {
    config_set 'output_device' 'plughw:1'

    handle_root_platform 'chip'
}