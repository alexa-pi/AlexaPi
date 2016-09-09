### Always-on monitoring

If you select to install always-on monitoring, the system will re-spawn AlexaPi anytime it crashes.
This is useful for a stand-alone device, but probably too heavy-handed if you want to use the Pi for anything else.

To prevent the re-spawn from happening, add a file called "dont_start" into the /tmp directory: `touch /tmp/dont_start`
This will kill prevent the script from creating a new instance of main.py, and a "kill" command will now truly kill the alexa program.  `rm /tmp/dont_start` will return to re-spawning.

After a reboot, AlexaPi will be restarted and re-spawned as usual.

### A note on Shairport-sync

By default, shairport-sync (the airplay client) uses port 5000.  This is no problem if everything goes as planned, but AlexaPi's authorization on sammachin's design uses port 5000 as well, and if shairport-sync is running while that happens, everything fails.

As a result, I have changed the authorization port for AlexaPi to 5050.  Note that you will have to change the settings within the developer website for this to work.

### Advanced Install

For those of you that prefer to install the code manually or tweak things here's a few pointers...

The Amazon AVS credentials are stored in a file called creds.py which is used by auth_web.py and main.py, there is an example with blank values.

The auth_web.py is a simple web server to generate the refresh token via oAuth to the amazon users account, it then appends this to creds.py and displays it on the browser.

main.py is the 'main' alexa client it simply runs on a while True loop waiting either the trigger word "Alexa," or for the button to be pressed. It then records audio and when the button is released (or 5 seconds has passed in the case of the trigger word) it posts this to the AVS service using the requests library, When the response comes back it is played back using vlc via an os system call. 

The LED's are a visual indictor of status, I used a duel Red/Green LED but you could also use separate LEDS, Red is connected to GPIO 24 and green to GPIO 25, When recording the RED LED will be lit when the file is being posted and waiting for the response both LED's are lit (or in the case of a dual R?G LED it goes Yellow) and when the response is played only the Green LED is lit. If The client gets an error back from AVS then the Red LED will flash 3 times.

The internet_on() routine is testing the connection to the Amazon auth server as I found that running the script on boot it was failing due to the network not being fully established so this will keep it retrying until it can make contact before getting the auth token.

The auth token is generated from the request_token the auth_token is then stored in a local memcache with and expiry of just under an hour to align with the validity at Amazon, if the function fails to get an access_token from memcache it will then request a new one from Amazon using the refresh token.
