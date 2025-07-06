#!/bin/bash

killall python3
sleep 1
nohup python3 main.py > main.log 2>&1 &
sleep 1
nohup python3 standalone_services/google_sheet.py > google_sheet.log 2>&1 &

echo "Bot services started"
