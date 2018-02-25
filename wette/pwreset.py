#!/usr/bin/env python3

from flask_app import app
import hashlib

print(hashlib.md5(bytes(app.config['PASSWORD_SALT'] + 'X_c2hUi9', 'utf-8')).hexdigest())
