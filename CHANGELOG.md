# Change Log
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/).

## [Unreleased]

## [1.5] - 2017-03-10
Please run the installation script again to install / upgrade all the dependencies. 
There are no config changes this time. 
Run the `auth_web.py` again after the install (when keeping a config) for your device to appear separately in the Alexa app. 

### Changed
- On Debian-based systems, the `python-pip` package gets uninstalled and `pip` is installed via `easy_install` instead to get the latest version.
- Recorded audio is now streamed to AVS instead of recording the whole thing and then sending it at once.
    - Brings huge speed improvement (response latency).
    - This means that when your recording LED (or whatever your device equivalent) is on, data gets sent to Amazon already.
    - Used code from @respeaker (thank you!).
- Changed the device ID in auth_web to use a unique ID for the HW from UUID.getnode() to allow multiple devices on one account, this ID is a hashed version of one of the devices MAC addresses.
- Changed hello.mp3 to 24Khz Mono to match the other files

### Fixed
- Updated old versions of requirements in `requirements.txt`. Also fixes `ImportError: No module named cheroot.server`.

## [1.4] - 2017-03-01
Please update your config according to the [Configuration changes] section on the wiki or better, do a new clean installation with a fresh config.

### Added
- Startup, pre-interaction, post-interaction and shutdown commands. Can be used to adjust shairport-sync volume for example (see `config.template.yaml`)
- dependency on the _coloredlogs_ Python library
- Now configurable (in the configuration file):
	- logging level
	- pocketsphinx's threshold
- Newly supported platforms:
    - _hyperion_ - Allows status visualization with [Hyperion](https://hyperion-project.org).
    - _serial_ - This can be used for a device that uses Arduino for example - like the Teddy Ruxpin project Tedlexa for which there is the default setting in the config template.
- SoX playback handler in addition to the existing VLC handler 
    - This should fix/improve issues with audio on Orange Pi and CHIP (see also the `playback_padding` config option)
    - TuneIn support is experimental and will be improved in the future
- Validation of the `input_device` configuration option. If the device is considered invalid, AlexaPi exists with a list of valid options for you to choose. Can be overriden by a new option `allow_unlisted_input_device`.

### Changed
- Refactored triggering:
    - Split into modules. Standalone user triggers are now possible.
    - Each trigger can be enabled / disabled. Voice triggering is therefore now optional (although enabled by default).
- Use Python logging instead of prints to stdout
- Changed default pocketsphinx's threshold in the config template from 1e-5 to 1e-10, which should bring better trigger word recognition with hopefully no (or very few) _false triggers_
- The setup doesn't ask about enabling automatic restart of AlexaPi anymore. It can be enabled manually as described in the [Restart on crashes](https://github.com/alexa-pi/AlexaPi/wiki/Restart-on-crashes) section in the [Documentation].

### Removed
- unused dependencies; if you haven't used it for anything else, you can safely disable it and uninstall:
    - memcached (as of this version)
        - `sudo systemctl stop memcached`
        - `sudo pip uninstall python-memcached`
        - (Debian) `sudo apt-get remove memcached`
        - (Arch Linux) `sudo pacman -R memcached`
    - Wave: `sudo pip uninstall Wave`
    - wsgiref: `sudo pip uninstall wsgiref`
    - py-getch: `sudo pip uninstall py-getch`

## [1.3.1] - 2017-01-01
This is mainly a test of doing bugfix releases.

### Fixed
- Error message in setup when the device _other_ is selected.

## [1.3] - 2016-12-21
- **IMPORTANT**: This is a major rewrite that requires you to delete the whole old version and set up the new one from scratch. See the [Migration quick-guide](https://github.com/alexa-pi/AlexaPi/wiki/Migration) for help.
- A lot of refactoring and changes for better future development.

### Added
- [Documentation] for users and developers. Also, there are [guidelines / tips for contributors](https://github.com/alexa-pi/AlexaPi/blob/master/CONTRIBUTING.md).
- Native systemd support (added a service unit file). This brings better security and is easier and convenient.
- Can run under an unprivileged user for better security.
- Newly supported platforms (apart from Raspberry Pi):
    - Orange Pi and other A20 / H3 based boards
    - C.H.I.P.
    - _desktop_ platform, which is an interactive platform. Alexa can be triggered here with keyboard input.
    - _dummy_ platform that doesn't do anything (like touching GPIO hardware) and is daemon-friendly.
    - Magic Mirror
    - See the [Devices] section in the [Documentation] for further details.
- Now configurable (in the configuration file):
    - Custom command and duration for the _long_press_ feature (e.g. shutting down the Pi after 10s button press)
    - Platform trigger voice confirmation (you can set whether you want to hear Alexa's _yes_ after you press a button)
    - Audio output device
    - Default volume
- Different audio output devices for speech and media can be specified.
- Support for Arch Linux.

### Changed
- Improved directory structure.
- Paths improvements for better _platform-independency_ and UX.
    - Use system temporary directory for recordings/answers, which is usually in RAM to avoid using system storage.
    - Default install path is now _/opt/AlexaPi_.
- Uses pocketsphinx only from PyPI (not the extra `git pull` anymore), which saves about 200 MB on bandwidth and 250 MB in storage space.
- More detailed documentation regarding Amazon device registration.
- All configuration in a single YAML file, which among other things enables users to update the python files without worrying.
- Better UX when running setup with existing config.
- Runs via systemd by default. Other options can be selected in setup.
- Runs under an unprivileged user _alexapi_ by default. Can be changed in init scripts / unit files.
- There is no default command for the _long_press_ feature.
- Abstracted device platform code into **_device_platforms_** which means we can now support other devices within the same codebase and users can now write their own independent device platform files.
- Abstracted playback library into **_playback_handlers_** which means we can now support multiple libraries within the same codebase and users can now write their own independent handlers and can route their sound through whatever they want to.

### Removed
- Temporarily disabled voice confirmation of the _long_press_ feature.

### Fixed
- Fixed not playing files with colons in their name. This resulted in not playing certain Alexa responses like when requesting _Flash Briefing_.
- Fixed overlapping audio playbacks / not playing some files. Partially caused by previous fix.
- Fixed incorrect handling of AVS responses that contained a _further-input-request_. This fixes skills like Jeopardy for example.

## [1.2] - 2016-08-30
@maso27 made significant changes that lead to this version.

### Added
- Voice Recognition via CMU Sphinx. When the word _"alexa"_ is detected, Alexa responds with _"Yes"_ and the subsequent audio to be processed.
- Option for the user to install shairport-sync for airplay support.
- A ten-second button press will trigger a system halt.
- Option to monitor Alexa continuously and re-start if it has died.
- Command line arguments:
 `(-s / --silent)` = start without saying "Hello"
 `(-d / --debug)` = enable display of debug messages at command prompt
- Volume control via "set volume xx" where xx is between 1 and 10

### Changed
- Tunein support is improved.

## 1.1 - 2016-05-01
@sammachin created the project in January 2016 and made significant changes that lead to this version.


[Unreleased]: https://github.com/alexa-pi/AlexaPi/compare/v1.5...HEAD
[1.5]: https://github.com/alexa-pi/AlexaPi/compare/v1.4...v1.5
[1.4]: https://github.com/alexa-pi/AlexaPi/compare/v1.3...v1.4
[1.3.1]: https://github.com/alexa-pi/AlexaPi/compare/v1.3...v1.3.1
[1.3]: https://github.com/alexa-pi/AlexaPi/compare/v1.2...v1.3
[1.2]: https://github.com/alexa-pi/AlexaPi/compare/v1.1...v1.2
[Documentation]: https://github.com/alexa-pi/AlexaPi/wiki/
[Devices]: https://github.com/alexa-pi/AlexaPi/wiki/Devices
[Configuration changes]: https://github.com/alexa-pi/AlexaPi/wiki/Configuration-changes
