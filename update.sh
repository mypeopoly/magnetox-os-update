#!/bin/bash


update_os() {
    echo "Updating OS to newer version..."
    
    echo "Installing Qt development packages..."
    echo 'armbian' | sudo -S apt-get install -y qtbase5-dev qtchooser qt5-qmake qtbase5-dev-tools libqt5serialport5 libqt5serialport5-dev

    #Update KlipperScreen
    
    echo 'armbian' | sudo service KlipperScreen stop
    /home/pi/.KlipperScreen-env/bin/pip3 install sdbus
    /home/pi/.KlipperScreen-env/bin/pip3 install psutil
    /home/pi/.KlipperScreen-env/bin/pip3 install sdbus_networkmanager
    mv /home/pi/KlipperScreen /home/pi/KlipperScreen-backof
    git clone https://github.com/KlipperScreen/KlipperScreen /home/pi/KlipperScreen 
    cd /home/pi/KlipperScreen
    git checkout a7b8c4c
    
    if [ $? -ne 0 ]; then
        echo "Failed to install Qt development packages. Exiting..."
        exit 1
    fi
    
    echo "Qt development packages installed successfully."
    
    echo "Copying necessary files..."
    cd /home/pi/magnetox-os-update
    cp auto-uuid/*  /home/pi/auto-uuid/
    chmod +x /home/pi/auto-uuid/*.sh
    chmod +x /home/pi/auto-uuid/MagnetoWifiHelper
    chmod +x /home/pi/auto-uuid/Magmotor
    chmod +x /home/pi/auto-uuid/99-magneto-automount.rules
    chmod +x /home/pi/auto-uuid/magneto-automount
    cp config/* /home/pi/printer_data/config/
    cp config/Line_Purge.cfg /home/pi/printer_data/config/KAMP/
    cp KlipperScreen/* /home/pi/KlipperScreen/panels/
    echo 'armbian' | sudo cp -f ./auto-uuid/mainsail.cfg /home/pi/mainsail-config/mainsail.cfg
    echo 'armbian' | sudo cp ./auto-uuid/magneto-automount /usr/bin/magneto-automount
    echo 'armbian' | sudo chmod +x /usr/bin/magneto-automount
    echo 'armbian' | sudo cp ./auto-uuid/magneto-automount@.service /usr/lib/systemd/system/
    echo 'armbian' | sudo systemctl daemon-reload
    echo 'armbian' | sudo cp ./auto-uuid/99-magneto-automount.rules /etc/udev/rules.d/
    echo 'armbian' | sudo udevadm control --reload-rules
    echo "Files copied successfully."
    echo 'armbian' | sudo sync
    echo "OS and applications have been updated."
    echo 'armbian' | sudo reboot
}


current_version=$(curl -s http://127.0.0.1:8880/get_os_version | jq -r '.version')
echo "Current version from URL: $current_version"

file_version=$(cat /home/pi/magnetox-os-update/version.txt)
echo "Version from file: $file_version"

version_from_url=$(echo $current_version | grep -o 'v[0-9]\+\.[0-9]\+\.[0-9]\+')
version_from_file=$(echo $file_version | grep -o 'v[0-9]\+\.[0-9]\+\.[0-9]\+')


update_os


