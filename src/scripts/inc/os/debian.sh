#!/bin/bash

function install_os {
    apt-get update
    apt-get install curl git python-dev python-setuptools python-pip swig libasound2-dev libpulse-dev vlc-nox sox libsox-fmt-mp3 -y
}

function install_shairport-sync {

    apt-get install autoconf libdaemon-dev libasound2-dev libpopt-dev libconfig-dev avahi-daemon libavahi-client-dev libssl-dev libsoxr-dev -y

    install_shairport-sync_from_source
}
