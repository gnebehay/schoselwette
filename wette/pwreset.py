#!/usr/bin/env python3

import hashlib

from . import models
from . import app
from . import db

user_id = 1

user = models.User.query.filter_by(id=user_id).one_or_none()

user.password = hashlib.md5(bytes(app.config['PASSWORD_SALT'] + 'X_c2hUi9', 'utf-8')).hexdigest()

db.session.commit()
