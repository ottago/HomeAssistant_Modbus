#!/bin/bash

#rm -rf 
rsync -avr --delete --delete-excluded --exclude "__pycache__" homeassistant/custom_components/generic_modbus 192.168.9.222:~/Google-Drive/src/docker/HomeAssistant/config/custom_components/
