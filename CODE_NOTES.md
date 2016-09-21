## AlexaPi restart on crashes

**Warning:** If you encounter crashes with AlexaPi, please report them, so we can fix them. **That** is the solution. This feature exists as a last resort when for example the app crashes after several weeks of operation due to some memory leak and there is no obvious way to solve it.

### SystemD

This feature is controlled by a systemd unit override file _/etc/systemd/system/AlexaPi.service.d/restart.conf_.
If you wish to enable it: 
`sudo mv /etc/systemd/system/AlexaPi.service.d/restart.conf.disabled /etc/systemd/system/AlexaPi.service.d/restart.conf`
And to disable it: 
`sudo mv /etc/systemd/system/AlexaPi.service.d/restart.conf /etc/systemd/system/AlexaPi.service.d/restart.conf.disabled`

And `sudo systemctl daemon-reload` for the changes to take effect. 

### Classic init scripts

The feature is controlled by the presence of _/etc/opt/AlexaPi/monitor_enable_.
If you wish to enable it: `sudo touch /etc/opt/AlexaPi/monitor_enable`
And to disable it: `sudo rm /etc/opt/AlexaPi/monitor_enable`

#### temporary setting

To prevent the re-spawn from happening, add a file called _monitor_pause_ into the _/run/AlexaPi_ directory. 
`sudo touch /run/AlexaPi/monitor_pause` will do the job.
This will prevent the script from creating a new instance of AlexaPi, and a `kill` command will now truly kill the alexa program. 
`sudo rm /run/AlexaPi/monitor_pause` will return to re-spawning.

After a reboot, AlexaPi will be restarted and re-spawned as usual.

## A note on Shairport-sync

By default, shairport-sync (the airplay client) uses port 5000.  This is no problem if everything goes as planned, but AlexaPi's authorization on sammachin's design uses port 5000 as well, and if shairport-sync is running while that happens, everything fails.

As a result, I have changed the authorization port for AlexaPi to 5050.  Note that you will have to change the settings within the developer website for this to work.

## Configuration

Configuration of AlexaPi is stored in a file called _config.yaml_, which as the extension suggests uses the [YAML](http://yaml.org/) format. AlexaPi looks for this file in several locations:
- _/etc/opt/AlexaPi_
- the _src_ subdirectory of _AlexaPi_ installation (_AlexaPi/src_)

The last existing file in this ordered list will be used. That means normally _/etc/opt/AlexaPi/config.yml_ is used, but if you create _config.yaml_ in the latter paths, it will be used instead. 

## Advanced Install

For those of you that prefer to install the code manually or tweak things here's a few pointers...

The Amazon AVS credentials are stored in the configuration file called config.yaml which is used by auth_web.py and main.py, there is a template with blank values.

The auth_web.py is a simple web server to generate the refresh token via oAuth to the amazon users account, it then appends this to creds.py and displays it on the browser.

main.py is the 'main' alexa client it simply runs on a while True loop waiting either the trigger word "Alexa," or for the button to be pressed. It then records audio and when the button is released (or 5 seconds has passed in the case of the trigger word) it posts this to the AVS service using the requests library, When the response comes back it is played back using vlc via an os system call. 

The LED's are a visual indictor of status, I used a duel Red/Green LED but you could also use separate LEDS, Red is connected to GPIO 24 and green to GPIO 25, When recording the RED LED will be lit when the file is being posted and waiting for the response both LED's are lit (or in the case of a dual R?G LED it goes Yellow) and when the response is played only the Green LED is lit. If The client gets an error back from AVS then the Red LED will flash 3 times.

The internet_on() routine is testing the connection to the Amazon auth server as I found that running the script on boot it was failing due to the network not being fully established so this will keep it retrying until it can make contact before getting the auth token.

The auth token is generated from the request_token the auth_token is then stored in a local memcache with and expiry of just under an hour to align with the validity at Amazon, if the function fails to get an access_token from memcache it will then request a new one from Amazon using the refresh token.
