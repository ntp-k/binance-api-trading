#!/bin/bash

killall python3
sleep 1
nohup python3 main.py > main.log 2>&1 &
sleep 1
nohup python3 standalone_services/update_position_record_to_google_sheet.py > update_position_record.log 2>&1 &

echo "Bot services started"
