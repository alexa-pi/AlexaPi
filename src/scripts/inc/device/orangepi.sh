#!/bin/bash

# shellcheck disable=SC2034
DESCRIPTION="Orange Pi or another H3 based board"

function install_device {
    run_pip install git+https://github.com/duxingkei33/orangepi_PC_gpio_pyH3.git
}

function install_device_config {
    handle_root_platform 'orangepi'
}