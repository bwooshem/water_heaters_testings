#!/bin/bash

# CTA-2045 UCM Installer Script
# Author: Brian Woo-Shem, LBNL
# Updated: 20250828
# Prerequisites: Working installation of Raspberry Pi OS on a Raspberry Pi board. 
# - The user must be named "pi" and have sudoer permission
# - water_heaters_testings folder must be installed in the home directory 
# For more info, see https://docs.google.com/document/d/1difERG2kKaJZgSYxNnHF-rqGF5J3Jq3UfMOjikmHY0M/edit?tab=t.0
# Installs code from the following sources:
# - CTA2045 UCM C++ Library v.1.00, which is Copyright (c) 2016, Electric Power Research Institute (EPRI) and released under the BSD 3 Clause license. See https://github.com/PortlandStatePowerLab/water_heaters_testings/blob/main/dcs/LICENSE
# - water_heaters_testings, (c) Portland State Power Lab. See https://github.com/PortlandStatePowerLab/water_heaters_testings/tree/main


echo "CTA-2045 UCM Installer Script"

#line for error handling
set -euo pipefail

# --------------------------------------------------------------------------
# Ensure script is being run as sudo
# --------------------------------------------------------------------------
if [[ $EUID -ne 0 ]]; then
    echo "Error: The installer must be run with sudo or as root." >&2
    exit 1
fi

# --------------------------------------------------------------------------
# Update
# --------------------------------------------------------------------------
echo -e "Updating the Pi and restarting is recommended before running this script. Have you already updated and restarted? [y/n]"
read choice

if [ "$choice" != "${choice#[Nn]}" ]; then
	echo -e "Would you like this script to apply updates now? [y/n]"
	read choice2
	if [ "$choice2" != "${choice2#[Yy]}" ]; then
		sudo apt update
		sudo apt upgrade -y
		echo -e "Updates Complete!"
		echo -e "\n*** Alert: Please restart your Raspberry Pi, then run this script again ***\n"
		exit 0
	else
		echo -e "\n*** WARNING: Installation will proceed, however there is a risk something goes wrong due to out of date software ***\n"
		echo "Use Ctrl + c if you do NOT want to proceed "
		sleep 2
	fi
fi

# --------------------------------------------------------------------------
# Install basic dependencies
# --------------------------------------------------------------------------
sudo apt install vim tmux g++ cmake make -y

# --------------------------------------------------------------------------
# Install WiringPi (dependency)
# --------------------------------------------------------------------------
# Define the URL and filename
URL="https://github.com/WiringPi/WiringPi/releases/download/3.16/wiringpi_3.16_armhf.deb"
FILENAME="wiringpi_3.16_armhf.deb"

# Download the file
echo "Downloading $FILENAME..."
wget "$URL" -O "$FILENAME"

# Check if download was successful
if [ $? -ne 0 ]; then
    echo "Error: Failed to download the file"
    exit 1
fi

# Install the package
echo "Installing $FILENAME..."
sudo dpkg -i "$FILENAME"

# Handle any dependency issues
if [ $? -ne 0 ]; then
    echo "Fixing dependencies..."
    sudo apt-get install -f -y
fi

# Clean up (optional - remove the downloaded file)
echo "Cleaning up..."
rm -f "$FILENAME"

echo "Installation complete!"


# --------------------------------------------------------------------------
# Enable SPI 
# --------------------------------------------------------------------------
#  1. Use raspi‑config's non‑interactive mode 
#   do_spi 0  → enable SPI (0 = enable, 1 = disable)
echo "Enabling SPI via raspi-config..."
raspi-config nonint do_spi 0 >/dev/null

#  2. Load the driver
echo "Loading spidev module..."
modprobe spidev || echo "spidev already loaded."

#  3. Check status 
echo "=== SPI status ==="
if grep -q "^dtparam=spi=on" /boot/config.txt; then
    echo "config.txt: dtparam=spi=on   (OK)"
else
    echo "config.txt: dtparam=spi=on   (missing!)"
fi

if lsmod | grep -q "^spidev"; then
    echo "Kernel module: spidev loaded"
else
    echo "Kernel module: spidev NOT loaded"
fi
# Note: Pi must be rebooted before SPI changes take effect

# --------------------------------------------------------------------------
# Begin UCM code installation
# --------------------------------------------------------------------------
# go to the directory if we're not there already
cd /home/pi/water_heaters_testings/dcs
# Install Debug w/Test and Sample
# following build instructions from https://github.com/PortlandStatePowerLab/water_heaters_testings/tree/main/dcs
mkdir -p build/debug
cd build/debug
cmake -DCMAKE_BUILD_TYPE=Debug -DSAMPLE=1 -DTEST=1 ../../
make

echo -e "\nInstallation Completed Successfully! :)\n"
echo -e "\n*** Alert: Please restart your Raspberry Pi before using the launcher script ***\n"
echo -e "[info] To run the launcher, go to water_heaters_testings/dcs/build/debug \n      Then run \$ sudo launcher.py"