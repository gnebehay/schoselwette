#!/bin/bash

rm -rf venv
pyvenv venv
venv/bin/pip3 install --upgrade pip
venv/bin/pip3 install --upgrade wheel
venv/bin/pip3 install --upgrade -r requirements.txt
venv/bin/pip3 install -e git+https://github.com/nathancahill/flask-inputs.git#egg=Flask-Inputs
