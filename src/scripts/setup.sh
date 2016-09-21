#!/bin/bash

pushd `dirname $0`/../ > /dev/null
ALEXASRC_DIRECTORY=`pwd -P`
popd > /dev/null

SCRIPT_DIRECTORY=$ALEXASRC_DIRECTORY/scripts
TMP_DIR="/tmp"
ALEXASRC_DIRECTORY_CORRECT="/opt/AlexaPi/src"
CONFIG_SYSTEM_DIRECTORY="/etc/opt/AlexaPi"
CONFIG_FILENAME="config.yaml"
CONFIG_FILE_SYSTEM="${CONFIG_SYSTEM_DIRECTORY}/${CONFIG_FILENAME}"
CONFIG_FILE_LOCAL="./${CONFIG_FILENAME}"

RUN_USER="alexapi"

if [ "$EUID" -ne 0 ]
	then echo "Please run as root"
	exit
fi

if [ "$ALEXASRC_DIRECTORY" != "$ALEXASRC_DIRECTORY_CORRECT" ]; then

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

else

    echo "Do you want AlexaPi to run on boot?"
	echo "You have these options: "
	echo "0 - NO"
	echo "1 - yes, use systemd (default, RECOMMENDED and awesome)"
	echo "2 - yes, use a classic init script (for a very old PC or an embedded system)"
	read -p "Which option do you prefer? [hit Enter for 1]: " init_type

    if [ "${init_type// /}" != "0" ]; then

        if [ "${init_type}" == "" ]; then
            init_type="1"
        fi

        read -p "Would you like to have AlexaPi restart when it crashes? (y/N)? " monitorAlexa

        echo -n "Creating a user to run AlexaPi under ... "
        UID_TEST=`id -u $RUN_USER >/dev/null 2>&1`
        UID_TEST="$?"

        if [ $UID_TEST -eq 0 ]; then
            echo "user already exists. That's cool - using that."
        else
            useradd --system --user-group $RUN_USER 2>/dev/null
            gpasswd -a $RUN_USER gpio > /dev/null
            gpasswd -a $RUN_USER audio > /dev/null
            if [ "$?" -eq "0" ]; then
                echo "done."
            else
                echo "unknown error. useradd returned code $?."
            fi
        fi

        cd $SCRIPT_DIRECTORY
        chmod +x *.sh

        case $init_type in
            2 ) # classic
                install -Dm744 initd_alexa.sh /etc/init.d/AlexaPi

                mkdir -p /etc/opt/AlexaPi
                touch /etc/opt/AlexaPi/.keep
                if [ "$monitorAlexa" == "y" ] || [ "$monitorAlexa" == "Y" ]; then
                    touch /etc/opt/AlexaPi/monitor_enable
                fi

                touch /var/log/AlexaPi.log

                update-rc.d AlexaPi defaults
            ;;

            * ) # systemd
                install -Dm644 ./AlexaPi.service /usr/lib/systemd/system/AlexaPi.service
                install -Dm644 ./restart.conf /etc/systemd/system/AlexaPi.service.d/restart.conf.disabled

                if [ "$monitorAlexa" == "y" ] || [ "$monitorAlexa" == "Y" ]; then
                    mv /etc/systemd/system/AlexaPi.service.d/restart.conf.disabled /etc/systemd/system/AlexaPi.service.d/restart.conf
                fi

                systemctl daemon-reload
                systemctl enable AlexaPi.service
            ;;
        esac

    fi

fi

read -p "Would you like to also install Airplay support (Y/n)? " shairport

apt-get update
apt-get install wget git -y

cd $ALEXASRC_DIRECTORY
wget --output-document ./vlc.py "http://git.videolan.org/?p=vlc/bindings/python.git;a=blob_plain;f=generated/vlc.py;hb=HEAD"
apt-get install python-dev swig libasound2-dev memcached python-pip python-alsaaudio vlc libpulse-dev python-yaml -y
pip install -r ./requirements.txt

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

cd ${ALEXASRC_DIRECTORY}
echo ""

if [ "${ALEXASRC_DIRECTORY}" == "${ALEXASRC_DIRECTORY_CORRECT}" ]; then
    mkdir -p ${CONFIG_SYSTEM_DIRECTORY}
    touch ${CONFIG_SYSTEM_DIRECTORY}/.keep
    CONFIG_FILE="${CONFIG_FILE_SYSTEM}"

    if [ -f ${CONFIG_FILE_LOCAL} ]; then
        echo "WARNING: You are installing AlexaPi into system path (${ALEXASRC_DIRECTORY_CORRECT}), but local configuration file (${CONFIG_FILE_LOCAL}) exists and it will shadow the system one (the local will be used instead of the system one, which is ${CONFIG_FILE_SYSTEM}). If this is not what you want, rename, move or delete the local configuration."
    fi
else
    CONFIG_FILE="${CONFIG_FILE_LOCAL}"
fi

config_action=2
if [ -f $CONFIG_FILE ]; then
    echo "Configuration file $CONFIG_FILE exists already. What do you want to do?"
    echo "[0] Keep and use current configuration file."
    echo "[1] Edit existing configuration file."
    echo "[2] Delete the configuration file and start with a fresh one."
	read -p "Which option do you prefer? [hit Enter for 0]: " config_action
fi

declare -A config_defaults
config_defaults[DeviceTypeID]=""
config_defaults[SecurityProfileDescription]=""
config_defaults[SecurityProfileID]=""
config_defaults[ClientID]=""
config_defaults[ClientSecret]=""

case ${config_action} in

    1)
        echo "Editing existing configuration file ..."
        echo "Hit Enter to fill in the current value (in brackets)."

        config_defaults[DeviceTypeID]="`grep -o -P "(?<=ProductID:).*" ${CONFIG_FILE} | sed 's/^ *//;s/ *$//;s/"//g'`"
        config_defaults[SecurityProfileDescription]="`grep -o -P "(?<=Security_Profile_Description:).*" ${CONFIG_FILE} | sed 's/^ *//;s/ *$//;s/"//g'`"
        config_defaults[SecurityProfileID]="`grep -o -P "(?<=Security_Profile_ID:).*" ${CONFIG_FILE} | sed 's/^ *//;s/ *$//;s/"//g'`"
        config_defaults[ClientID]="`grep -o -P "(?<=Client_ID:).*" ${CONFIG_FILE} | sed 's/^ *//;s/ *$//;s/"//g'`"
        config_defaults[ClientSecret]="`grep -o -P "(?<=Client_Secret:).*" ${CONFIG_FILE} | sed 's/^ *//;s/ *$//;s/"//g'`"
    ;;
    2)
        echo "Creating configuration file ${CONFIG_FILE} ..."
        cp config.template.yaml ${CONFIG_FILE}
    ;;
    *)
        echo "Exiting ..."
        exit
    ;;

esac

read -p "Enter your Device Type ID [${config_defaults[DeviceTypeID]}]: " DeviceTypeID
if [ "${DeviceTypeID}" == "" ]; then
    DeviceTypeID="${config_defaults[DeviceTypeID]}"
fi
sed -i -e 's/ProductID.*/ProductID: "'"${DeviceTypeID}"'"/g' $CONFIG_FILE

read -p "Enter your Security Profile Description [${config_defaults[SecurityProfileDescription]}]: " SecurityProfileDescription
if [ "${SecurityProfileDescription}" == "" ]; then
    SecurityProfileDescription="${config_defaults[SecurityProfileDescription]}"
fi
sed -i -e 's/Security_Profile_Description.*/Security_Profile_Description: "'"${SecurityProfileDescription}"'"/g' $CONFIG_FILE

read -p "Enter your Security Profile ID [${config_defaults[SecurityProfileID]}]: " SecurityProfileID
if [ "${SecurityProfileID}" == "" ]; then
    SecurityProfileID="${config_defaults[SecurityProfileID]}"
fi
sed -i -e 's/Security_Profile_ID.*/Security_Profile_ID: "'"${SecurityProfileID}"'"/g' $CONFIG_FILE

read -p "Enter your Client ID [${config_defaults[ClientID]}]: " ClientID
if [ "${ClientID}" == "" ]; then
    ClientID="${config_defaults[ClientID]}"
fi
sed -i -e 's/Client_ID.*/Client_ID: "'"${ClientID}"'"/g' $CONFIG_FILE

read -p "Enter your Client Secret [${config_defaults[ClientSecret]}]: " ClientSecret
if [ "${ClientSecret}" == "" ]; then
    ClientSecret="${config_defaults[ClientSecret]}"
fi
sed -i -e 's/Client_Secret.*/Client_Secret: "'"${ClientSecret}"'"/g' $CONFIG_FILE

python ./auth_web.py
