#!/bin/bash

pushd `dirname $0`/../ > /dev/null
ALEXASRC_DIRECTORY=`pwd -P`
popd > /dev/null

SCRIPT_DIRECTORY=$ALEXASRC_DIRECTORY/scripts
TMP_DIR="/tmp"
ALEXASRC_DIRECTORY_CORRECT="/opt/AlexaPi/src"

if [ "$EUID" -ne 0 ]
	then echo "Please run as root"
	exit
fi

CORRECT_INSTALL_PATH=true
if [ "$ALEXASRC_DIRECTORY" != "$ALEXASRC_DIRECTORY_CORRECT" ]; then

    CORRECT_INSTALL_PATH=false

    echo "You haven't downloaded AlexaPi into /opt. As a result of that, you won't be able to run AlexaPi on boot."
    echo "If you wish to be able to run AlexaPi on boot, please interrupt this script and download into /opt."
    echo ""
    echo "Note: If you're an advanced user, you can install the init script manually and edit it to reflect your install path, but we don't provide any guarantees."
    read -p "Interrupt? (Y/n)? " interrupt_script

    case $interrupt_script in
            [nN] )
                echo "Carrying on ..."
            ;;
            * )
                echo "Script interrupted. Please download AlexaPi into /opt as in project documentation."
                exit
            ;;
    esac
fi

cd $SCRIPT_DIRECTORY
chmod +x *.sh

read -p "Would you like to also install Airplay support (Y/n)? " shairport
case $shairport in
        [nN] ) 
        	echo "shairport-sync (Airplay) will NOT be installed."
        ;;
        * )
        	echo "shairport-sync (Airplay) WILL be installed."
        ;;
esac

if [ "$CORRECT_INSTALL_PATH" == true ]; then

    read -p "Would you like to add always-on monitoring (y/N)? " monitorAlexa
    case $monitorAlexa in
            [yY] )
                echo "monitoring WILL be installed."
            ;;
            * )
                echo "monitoring will NOT be installed."
            ;;
    esac

fi

apt-get update
apt-get install wget git -y

cd $ALEXASRC_DIRECTORY
wget --output-document ./vlc.py "http://git.videolan.org/?p=vlc/bindings/python.git;a=blob_plain;f=generated/vlc.py;hb=HEAD"
apt-get install python-dev swig libasound2-dev memcached python-pip python-alsaaudio vlc libpulse-dev -y
pip install -r ./requirements.txt

touch /var/log/alexa.log

case $shairport in
        [nN] ) ;;
        * )
                echo "--building and installing shairport-sync--"
                cd $TMP_DIR

                apt-get install autoconf libdaemon-dev libasound2-dev libpopt-dev libconfig-dev avahi-daemon libavahi-client-dev libssl-dev libsoxr-dev -y

                git clone https://github.com/mikebrady/shairport-sync.git
                cd shairport-sync
                autoreconf -i -f
                ./configure --with-alsa --with-avahi --with-ssl=openssl --with-soxr --with-metadata --with-pipe --with-systemd
                make
                getent group shairport-sync &>/dev/null || sudo groupadd -r shairport-sync >/dev/null
                getent passwd shairport-sync &> /dev/null || sudo useradd -r -M -g shairport-sync -s /usr/bin/nologin -G audio shairport-sync >/dev/null
                make install

                systemctl enable shairport-sync

                rm -rf $TMP_DIR/shairport-sync
        ;;
esac

if [ "$CORRECT_INSTALL_PATH" == true ]; then

    cd $SCRIPT_DIRECTORY
    case $monitorAlexa in
            [yY] )
            cp initd_alexa_monitored.sh /etc/init.d/AlexaPi
        ;;
            * )
            cp initd_alexa.sh /etc/init.d/AlexaPi
            ;;
    esac

    update-rc.d AlexaPi defaults

fi

cd $ALEXASRC_DIRECTORY

echo "--Creating creds.py--"
echo "Enter your Device Type ID:"
read productid
echo ProductID = \"$productid\" > creds.py

echo "Enter your Security Profile Description:"
read spd
echo Security_Profile_Description = \"$spd\" >> creds.py

echo "Enter your Security Profile ID:"
read spid
echo Security_Profile_ID = \"$spid\" >> creds.py

echo "Enter your Client ID:"
read cid
echo Client_ID = \"$cid\" >> creds.py

echo "Enter your Client Secret:"
read secret
echo Client_Secret = \"$secret\" >> creds.py

python ./auth_web.py
