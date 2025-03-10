#!/bin/sh

echo "Применение миграций..."
python manage.py migrate --no-input

echo "Сбор статики бекенда..."
python manage.py collectstatic --no-input

echo "Запуск Gunicorn сервера..."
exec gunicorn --bind 0.0.0.0:8001 foodgram.wsgi
