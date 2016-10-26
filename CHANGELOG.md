# Change Log
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/).

## [Unreleased]
- **IMPORTANT**: This is a major rewrite that requires you to delete the whole old version and set up the new one from scratch. See the [Migration quick-guide](https://github.com/alexa-pi/AlexaPi/wiki/Migration) for help.
- A lot of refactoring and changes for better future development.

### Added
- Documentation regarding contributing.
- Native systemd support (added a service unit file). This brings better security and is easier and convenient.
- Can run under an unprivileged user for better security.
- Abstracted device platform code into **_device_platforms_** which means we can now support other devices within the same codebase.
- Added a simple _desktop_ platform, which enables people to run AlexaPi on other devices than Raspberry Pi. Alexa can be triggered here with keyboard input.
- Support for custom command and duration for the _long_press_ feature (e.g. shutting down the Pi after 10s button press).
- Platform voice confirmation is configurable (you can set whether you want to hear Alexa's _yes_ after you press a button).
- Added support for Orange Pi and other A20 / H3 based boards. See the [Devices] section in the [Documentation].

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

### Removed
- Temporarily disabled voice confirmation of the _long_press_ feature.

### Fixed
- Fixed not playing files with colons in their name. This resulted in not playing certain Alexa responses like when requesting _Flash Briefing_.

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


[Unreleased]: https://github.com/alexa-pi/AlexaPi/compare/v1.2...HEAD
[1.2]: https://github.com/alexa-pi/AlexaPi/compare/v1.1...v1.2
[Devices]: https://github.com/alexa-pi/AlexaPi/wiki/Devices
[Documentation]: https://github.com/alexa-pi/AlexaPi/wiki/