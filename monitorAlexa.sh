#!/bin/sh

while :
do
        if [ -f /tmp/dont_start ]; then
                /etc/init.d/AlexaPi stop
                sleep 3
        elif ! pgrep python -a | grep main.py > /dev/null; then
                /etc/init.d/AlexaPi silent
                sleep 5
        fi
done
