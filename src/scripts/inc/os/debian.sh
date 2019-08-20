#!/bin/bash

function install_os {
    apt-get update
    apt-get install curl git build-essential python3-dev python3-pip python3-setuptools swig libpulse-dev portaudio19-dev libportaudio2 vlc-bin vlc-plugin-base sox libsox-fmt-mp3 -y
}

function install_shairport-sync {

    apt-get install autoconf libdaemon-dev libasound2-dev libpopt-dev libconfig-dev avahi-daemon libavahi-client-dev libssl-dev libsoxr-dev -y

    install_shairport-sync_from_source
}
