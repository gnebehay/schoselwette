# Use an official Python runtime as a parent image
FROM python:3.8-slim

EXPOSE 8000

# Set the working directory to /app
WORKDIR /app

RUN pip install gunicorn==20.0.*

COPY ./requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . /app

ENV PYTHONUNBUFFERED 1
ENV FLASK_APP wette

CMD gunicorn -b 0.0.0.0:8000 wette:app
