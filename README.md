# AlexaPi (the new & awesome version)

This is a client for Amazon's Alexa service. It is intended and tested to run on a wide range of platforms, such as Raspberry Pi, Orange Pi, CHIP and ordinary Linux desktops.

### NOTE: This is a new generation of the project under heavy development. It is eventually gonna be more awesome than ever! Please bear with us while we stabilize the new code base.

### Do you want to help out? Read the [Contribution Guide](CONTRIBUTING.md).
### If you're interested in the things under the hood, check out the [Code Notes](CODE NOTES.md).

## Requirements

You will need:
### A Linux box

* a Raspberry Pi and an SD Card with a fresh install of Raspbian
* or an Orange Pi with Armbian
* or pretty much any up-to-date Linux system

### Audio peripherals

* external speaker with 3.5mm Jack
* USB Sound Dongle and microphone

### Other

* (optional) (Raspberry Pi) a push button connected between GPIO 18 and GND
* (optional) (Raspberry Pi) a dual colour LED (or 2 signle LEDs) connected to GPIO 24 & 25


Next you need to obtain a set of credentials from Amazon to use the Alexa Voice service.

- Login at `http://developer.amazon.com` and go to `Alexa`, then `Alexa Voice Service`.
- You need to create a new product type as a `Device`. For the ID use something like _AlexaPi_. Create a new security profile and under the `Web Settings`, there is `Allowed Origins` - put there `http://localhost:5050` and as `Allowed Return URLs` put `http://localhost:5050/code`. You can also create URLs replacing `localhost` with the IP of your box e.g. `http://192.168.1.123:5050`.
- Make a note of these credentials you will be asked for them during the install process

## Installation

**NOTE:** This is outdated and due to change!

1. Boot your PC and login to a command prompt.
2. Make sure you are in `/opt` by issuing

    ```
    cd /opt
    ```

3. Clone this repo
    
    ```
    git clone https://github.com/alexa-pi/AlexaPi.git
    ```
        
4. Run the setup script

    ```
    sudo ./setup.sh
    ```

Follow instructions...

Enjoy :)

## Issues/Bugs etc.

If your alexa isn't running on startup you can check /var/log/alexa.log for errrors.

If the error is complaining about alsaaudio you may need to check the name of your soundcard input device, use 
`arecord -L` 
The device name can be set in the settings at the top of main.py 

You may need to adjust the volume and/or input gain for the microphone, you can do this with 
`alsamixer`

Once the adjustments have been made, you can save the settings using
`alsactl store`

## Project history

- **September 2016**: A project was started to have a common code base across devices and services.

- **May/June 2016**: @maso27 made significant changes that lead to _version 1.2_ and started on work towards supporting snowboy.
    * Voice Recognition via CMU Sphinx.  When the word "alexa" is detected, Alexa responds with "Yes" and the subsequent audio to be processed.
    * Push button functionality still works the same as previously as well.
    * Option for the user to install shairport-sync for airplay support.
    * A ten-second button press will trigger a system halt.
    * Option to monitor for Alexa continuously and re-start if it has died.
    * Command line arguments added:
     `(-s / --silent)` = start without saying "Hello"
     `(-d / --debug)` = enable display of debug messages at command prompt
    * tunein support is improved
    * volume control via "set volume xx" where xx is between 1 and 10
     
- **January 2016**: @sammachin created the project and made significant changes that lead to _version 1.1_.

## Contributors
* [Sam Machin](http://sammachin.com)
* [Lenny Shirly](https://github.com/lennysh)
* [dojones1](https://github.com/dojones1)
* [Chris Kennedy](http://ck37.com)
* [Anand](http://padfoot.in)
* [Mason Stone](https://github.com/maso27)
* [Nascent Objects](https://github.com/nascentobjects)
* [René Kliment](https://github.com/renekliment)

If you feel your name should be here, please contact us.
