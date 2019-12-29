# Use an official Python runtime as a parent image
FROM python:3.7-slim

# Set the working directory to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

RUN pip install -r requirements.txt

# Install any needed packages specified in requirements.txt
#RUN helloworld.sh

EXPOSE 5000

# Define environment variable
#ENV NAME World

# Run app.py when the container launches
CMD ["FLASK_DEBUG=1 FLASK_APP=wette/flask_app.py ~/venv/bin/flask run --host=0.0.0.0"]
