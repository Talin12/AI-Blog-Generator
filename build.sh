#!/usr/bin/env bash
set -o errexit

apt-get update && apt-get install -y ffmpeg curl

pip install -r requirements.txt

echo "🔍 Testing YouTube connectivity..."
curl -I https://www.youtube.com/watch?v=dQw4w9WgXcQ \
  && echo "✅ YouTube reachable" \
  || echo "❌ YouTube NOT reachable"


python manage.py collectstatic --noinput
python manage.py migrate
