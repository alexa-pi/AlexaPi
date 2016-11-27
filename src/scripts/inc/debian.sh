#!/bin/bash

function install_os {
    apt-get update
    apt-get install git python-dev python-setuptools python-pip swig libasound2-dev libpulse-dev vlc-nox memcached -y
}

function install_shairport-sync {

    apt-get install autoconf libdaemon-dev libasound2-dev libpopt-dev libconfig-dev avahi-daemon libavahi-client-dev libssl-dev libsoxr-dev -y

    install_shairport-sync_from_source
}
