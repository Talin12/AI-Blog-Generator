#!/usr/bin/env bash
set -o errexit

# Remove unnecessary packages
pip install -r requirements.txt

# Only migrate if using SQLite (no need for apt-get)
python manage.py collectstatic --noinput
python manage.py migrate