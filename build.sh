#!/usr/bin/env bash
set -o errexit

apt-get update && apt-get install -y ffmpeg curl

pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate
