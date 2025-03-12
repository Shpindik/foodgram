FROM python:3.9

WORKDIR /app/foodgram

RUN pip install gunicorn==20.1.0

COPY requirements.txt .

RUN pip install -r requirements.txt --no-cache-dir

COPY foodgram /app/foodgram

CMD gunicorn foodgram.wsgi:application --bind 0.0.0.0:8001