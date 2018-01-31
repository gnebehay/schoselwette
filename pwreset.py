#!venv/bin/python3

from wette import app
import hashlib

print(hashlib.md5(bytes(app.config['PASSWORD_SALT'] + 'PASSWORD', 'utf-8')).hexdigest())
