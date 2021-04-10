# Use an official Python runtime as a parent image
FROM python:3.8-slim

EXPOSE 8000

# Set the working directory to /app
WORKDIR /app

COPY ./requirements.txt /app/requirements.txt

ENV PYTHONUNBUFFERED 1

RUN pip install -r requirements.txt
RUN pip install gunicorn==20.0.*

# Copy the current directory contents into the container at /app
COPY . /app

CMD ./entrypoint.sh
