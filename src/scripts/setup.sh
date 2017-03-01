#!/bin/bash

set -o nounset # Fail when variable is used, but not initialized
set -o errexit # Fail on unhandled error exits
set -o pipefail # Fail when part of piped execution fails

pushd "$(dirname "$0")/../" > /dev/null
ALEXASRC_DIRECTORY=$(pwd -P)
popd > /dev/null

SCRIPT_DIRECTORY=$ALEXASRC_DIRECTORY/scripts
ALEXASRC_DIRECTORY_CORRECT="/opt/AlexaPi/src"
CONFIG_SYSTEM_DIRECTORY="/etc/opt/AlexaPi"
CONFIG_FILENAME="config.yaml"
CONFIG_FILE_SYSTEM="${CONFIG_SYSTEM_DIRECTORY}/${CONFIG_FILENAME}"
CONFIG_FILE_LOCAL="./${CONFIG_FILENAME}"

if [ "$EUID" -ne 0 ]; then
    echo "Please run as root"
	exit
fi

echo "TIP: When there is a value in brackets like [default_value], hit Enter to use it."
echo ""


if [ "$ALEXASRC_DIRECTORY" != "$ALEXASRC_DIRECTORY_CORRECT" ]; then

    echo "You haven't downloaded AlexaPi into /opt. As a result of that, you won't be able to run AlexaPi on boot."
    echo "If you wish to be able to run AlexaPi on boot, please interrupt this script and download into /opt."
    echo ""
    echo "Note: If you're an advanced user, you can install the init script manually and edit it to reflect your install path, but we don't provide any guarantees."
    read -r -p "Interrupt? (Y/n)? " interrupt_script

    case ${interrupt_script} in
            [nN] )
                echo "Carrying on ..."
            ;;
            * )
                echo "Script interrupted. Please download AlexaPi into /opt as in project documentation."
                exit
            ;;
    esac

fi

cd "${SCRIPT_DIRECTORY}"

OS_default="debian"
DEVICE_default="raspberrypi"

echo "Which operating system are you using?"
printf "%15s - %s\n" "debian" "Debian, Raspbian, Armbian, Ubuntu or other Debian-based"
printf "%15s - %s\n" "archlinux" "Arch Linux or Arch Linux-based"
read -r -p "Your OS [${OS_default}]: " OS

if [ "${OS}" == "" ]; then
    OS=${OS_default}
elif [ ! -f "./inc/os/${OS}.sh" ]; then
    echo "Incorrect value. Exiting."
    exit
fi

echo "Which device are you using?"
cd inc/device
for deviceFile in *.sh; do
    deviceName="${deviceFile/.sh/}"
    deviceDescription=$(grep -P -o -e "(?<=DESCRIPTION=\")(.*)(?=\")" "${deviceFile}")

    printf "%15s - %s\n" "${deviceName}" "${deviceDescription}"
done
cd "${SCRIPT_DIRECTORY}"

read -r -p "Your device [${DEVICE_default}]: " DEVICE

if [ "${DEVICE}" == "" ]; then
    DEVICE=${DEVICE_default}
elif [ ! -f "./inc/device/${DEVICE}.sh" ]; then
    echo "Incorrect value. Exiting."
    exit
fi

source ./inc/common.sh

# shellcheck disable=SC1090
source ./inc/os/${OS}.sh

# shellcheck disable=SC1090
source ./inc/device/${DEVICE}.sh

if [ "$ALEXASRC_DIRECTORY" == "$ALEXASRC_DIRECTORY_CORRECT" ]; then

    echo "Do you want AlexaPi to run on boot?"
	echo "You have these options: "
	echo "0 - NO"
	echo "1 - yes, use systemd (default, RECOMMENDED and awesome)"
	echo "2 - yes, use a classic init script (for a very old PC or an embedded system)"
	read -r -p "Which option do you prefer? [1]: " init_type

    if [ "${init_type// /}" != "0" ]; then

        if [ "${init_type}" == "" ]; then
            init_type="1"
        fi

        monitorAlexa=false

        create_user
        gpio_permissions

        cd "${SCRIPT_DIRECTORY}"

        case ${init_type} in
            2 ) # classic
                init_classic ${monitorAlexa}
            ;;

            * ) # systemd
                init_systemd ${monitorAlexa}
            ;;
        esac

    fi

fi

read -r -p "Would you like to also install Airplay support (Y/n)? " shairport

install_os

cd "${ALEXASRC_DIRECTORY}"

# This is here because of https://github.com/pypa/pip/issues/2984
if run_pip --version | grep "pip 1.5"; then
    run_pip install -r ./requirements.txt
else
    run_pip install --no-cache-dir -r ./requirements.txt
fi

install_device

case $shairport in
        [nN] ) ;;
        * )
                echo "-- installing shairport-sync --"
                install_shairport-sync
                systemctl enable shairport-sync
        ;;
esac

cd "${ALEXASRC_DIRECTORY}"
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
	read -r -p "Which option do you prefer? [hit Enter for 0]: " config_action
fi

case ${config_action} in

    1)
        echo "Editing existing configuration file ..."
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

install_device_config

declare -A config_defaults
config_defaults[Device_Type_ID]=$(config_get Device_Type_ID)
config_defaults[Security_Profile_Description]=$(config_get Security_Profile_Description)
config_defaults[Security_Profile_ID]=$(config_get Security_Profile_ID)
config_defaults[Client_ID]=$(config_get Client_ID)
config_defaults[Client_Secret]=$(config_get Client_Secret)

read -r -p "Enter your Device Type ID [${config_defaults[Device_Type_ID]}]: " Device_Type_ID
config_set 'Device_Type_ID' "${Device_Type_ID}"

read -r -p "Enter your Security Profile Description [${config_defaults[Security_Profile_Description]}]: " Security_Profile_Description
config_set 'Security_Profile_Description' "${Security_Profile_Description}"

read -r -p "Enter your Security Profile ID [${config_defaults[Security_Profile_ID]}]: " Security_Profile_ID
config_set 'Security_Profile_ID' "${Security_Profile_ID}"

read -r -p "Enter your Client ID [${config_defaults[Client_ID]}]: " Client_ID
config_set 'Client_ID' "${Client_ID}"

read -r -p "Enter your Client Secret [${config_defaults[Client_Secret]}]: " Client_Secret
config_set 'Client_Secret' "${Client_Secret}"


run_python ./auth_web.py

echo ""
echo "######################################################################################################"
echo "IMPORTANT NOTICE:"
echo "If you use a desktop OS, you HAVE TO set up your system audio so services like AlexaPi can use it too."
echo "See https://github.com/alexa-pi/AlexaPi/wiki/Audio-setup-&-debugging#pulseaudio"
echo "######################################################################################################"
echo ""