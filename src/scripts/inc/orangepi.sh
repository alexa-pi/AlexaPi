#!/bin/bash

function install_device {
    run_pip install git+https://github.com/duxingkei33/orangepi_PC_gpio_pyH3.git
}

function install_device_config {
    config_set 'input_device' 'default'

    handle_root_platform 'orangepi'
}