#!/bin/sh

if pgrep python -a | grep main.py > /dev/null; then
        echo "Alexa is already running."
else
        python /root/AlexaPi/main.py -s &
fi
