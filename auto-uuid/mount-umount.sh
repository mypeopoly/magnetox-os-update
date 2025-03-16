#!/bin/bash
if [ "$1" == "add" ]; then
    echo 'armbian' | sudo -S mkdir -p /home/pi/printer_data/gcodes/usb_disk
    echo 'armbian' | sudo -S chown pi:pi /home/pi/printer_data/gcodes/usb_disk
    echo 'armbian' | sudo -S mount -o uid=pi,gid=pi /dev/$2 /home/pi/printer_data/gcodes/usb_disk
elif [ "$1" == "remove" ]; then
    echo 'armbian' | sudo -S umount /home/pi/printer_data/gcodes/usb_disk
fi
