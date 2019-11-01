#!/usr/bin/env python3

import flask_app
import models
import hashlib

user_id = 1

user = flask_app.db_session.query(models.User).filter(models.User.id == user_id).one_or_none()

user.password = hashlib.md5(bytes(flask_app.app.config['PASSWORD_SALT'] + 'X_c2hUi9', 'utf-8')).hexdigest()

flask_app.db_session.commit()
