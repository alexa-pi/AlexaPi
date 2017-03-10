#!/bin/bash

function install_os {
    pacman -Sy
    pacman -S base-devel git python2 python2-pip swig alsa-lib alsa-utils libpulse vlc sox libmad libid3tag gcc --noconfirm --needed

    install -Dm644 ./unit-overrides/force-python2.conf /etc/systemd/system/AlexaPi.service.d/force-python2.conf
    systemctl daemon-reload
}

function install_shairport-sync {
    pacman -S shairport-sync --noconfirm --needed
}