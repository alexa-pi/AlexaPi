#!/bin/bash

function install_os {
    pacman -Sy
    pacman -S base-devel git python python-pip swig portaudio libpulse vlc sox libmad libid3tag gcc --noconfirm --needed

    systemctl daemon-reload
}

function install_shairport-sync {
    pacman -S shairport-sync --noconfirm --needed
}