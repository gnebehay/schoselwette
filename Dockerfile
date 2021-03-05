# Use an official Python runtime as a parent image
FROM python:3.8-slim

EXPOSE 8000

# Set the working directory to /app
WORKDIR /app
# Copy the current directory contents into the container at /app
COPY . /app

RUN pip install -r requirements.txt
RUN pip install gunicorn==20.0.*

CMD gunicorn -b 0.0.0.0:8000 wette:app
