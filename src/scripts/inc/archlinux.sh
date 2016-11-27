#!/bin/bash

function install_os {
    pacman -Sy
    pacman -S git python2 python2-pip swig alsa-lib alsa-utils libpulse vlc memcached gcc --noconfirm --needed

    install -Dm644 ./unit-overrides/force-python2.conf /etc/systemd/system/AlexaPi.service.d/force-python2.conf
    systemctl daemon-reload
    systemctl enable memcached
}

function install_shairport-sync {
    pacman -S shairport-sync --noconfirm --needed
}