#!/usr/bin/env bash
mkdir log
killall python
killall Python
source env/bin/activate
pip install -r requirements.txt
python channel.py play >> log/playlog.txt 2>&1 &
python channel.py fade >> log/fadelog.txt 2>&1 &
python server.py >> log/log.txt 2>&1 &
