import hashlib
import logging
import os
import random
import string

import flask
import flask_login
import requests
import sqlalchemy as sa

from flask_login import login_required
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import joinedload
from urllib.parse import quote

from .. import app
from .. import db
from .. import common
from .. import models

logger = logging.getLogger(__name__)

@app.route('/api/register', methods=['POST'])
def register():
    register_schema = {
        'type': 'object',
        'properties': {
            'email': {'type': 'string'},
            'password': {'type': 'string', 'minLength': 8},
            'firstName': {'type': 'string'},
            'lastName': {'type': 'string'}
        },
        'required': ['email', 'password', 'firstName', 'lastName']}

    posted_login = flask.request.get_json()

    validation_result = common.validate(posted_login, register_schema)
    if validation_result is not None: return validation_result

    if db.session.execute(
        sa.select(models.User).filter_by(email=posted_login['email'])
    ).scalar_one_or_none() is not None:
        return {'error': 'Email address is already in use.'}, 400

    user = models.User()
    user.email = posted_login['email']
    user.email_hash = hashlib.md5(bytes(user.email, 'utf-8')).hexdigest()
    user.first_name = posted_login['firstName']
    user.last_name = posted_login['lastName']
    user.paid = False

    salted_password = bytes(app.config['PASSWORD_SALT'] + posted_login['password'], 'utf-8')
    user.password = hashlib.md5(salted_password).hexdigest()

    db.session.add(user)

    user.create_missing_bets()

    common.send_mail_template('welcome.eml', recipients=[user.email], user=user)

    body = '{} {}, {}'.format(user.first_name, user.last_name, user.email)
    common.send_mail(subject='Neuer Schoselwetter', body=body, recipients=app.config['ADMIN_MAILS'])

    logger.info('User registered: %s, %s, %s', user.first_name, user.last_name, user.email)

    return {'success': True}


@app.route('/api/login', methods=['POST'])
def login():
    login_schema = {
        'type': 'object',
        'properties': {
            'email': {'type': 'string'},
            'password': {'type': 'string'},
            'rememberme': {'type': 'boolean'}
        },
        'required': ['email', 'password']}

    posted_login = flask.request.get_json()

    validation_result = common.validate(posted_login, login_schema)
    if validation_result is not None: return validation_result

    salted_password = bytes(app.config['PASSWORD_SALT'] + posted_login['password'], 'utf-8')
    password_hash = hashlib.md5(salted_password).hexdigest()

    user = db.session.execute(
        sa.select(models.User).filter_by(email=posted_login['email'], password=password_hash)
    ).scalar()

    if user is not None:

        if 'remember' in posted_login:
            remember = posted_login['remember']
        else:
            remember = False

        flask_login.login_user(user, remember=remember)

        logger.info('User logged in: %s', user.email)

        return flask.jsonify(success=True)

    return flask.jsonify(errors=["Oops, wrong login data."]), 401


@app.route('/api/logout', methods=['POST'])
def logout():
    flask_login.logout_user()
    return flask.jsonify(success=True)


@app.route('/api/trigger_password_reset', methods=['POST'])
def trigger_reset_password_user():

    trigger_reset_password_schema = {
        'type': 'object',
        'properties': {
            'email': {'type': 'string'}
        },
        'required': ['email']}

    posted_data = flask.request.get_json()

    validation_result = common.validate(posted_data, trigger_reset_password_schema)
    if validation_result is not None:
        return validation_result

    email = posted_data['email']

    try:
        user = db.session.execute(
            sa.select(models.User).filter_by(email=email)
        ).scalar_one()
    except NoResultFound:
        flask.abort(404)

    # Reset token is set irrespective of previous value
    user.reset_token = ''.join(random.choice(string.ascii_lowercase) for _ in range(8))

    common.send_mail_template('reset_password.eml', recipients=[user.email], user=user)

    logger.info('Password reset triggered for user: %s', user.email)

    return flask.jsonify(success=True)


@app.route('/api/reset_password', methods=['POST'])
def reset_password():

    reset_password_schema = {
        'type': 'object',
        'properties': {
            'user_id': {'type': 'integer'},
            'reset_token': {'type': 'string'},
            'new_password': {'type': 'string', 'minLength': 8}
        },
        'required': ['user_id', 'reset_token', 'new_password']}

    posted_json = flask.request.get_json()

    validation_result = common.validate(posted_json, reset_password_schema)
    if validation_result is not None:
        return validation_result

    user_id = posted_json['user_id']
    posted_reset_token = posted_json['reset_token']
    new_password = posted_json['new_password']

    user = db.session.execute(
        sa.select(models.User).filter_by(id=user_id)
    ).scalar_one()

    if user.reset_token is None or user.reset_token != posted_reset_token:
        flask.abort(403)

    salted_password = bytes(app.config['PASSWORD_SALT'] + new_password, 'utf-8')
    user.password = hashlib.md5(salted_password).hexdigest()

    user.reset_token = None

    logger.info('Password reset for user: %s', user.id)

    return flask.jsonify(success=True)


@app.route('/api/avatar/<seed>')
def get_avatar(seed):
    """
    Fetch or return cached avatar from DiceBear API.
    Avatars are cached in the cache/avatars directory.
    """
    cache_dir = os.path.join(os.path.dirname(__file__), '..', 'cache', 'avatars')

    seed_hash = hashlib.sha256(seed.encode('utf-8')).hexdigest()

    cache_file = os.path.join(cache_dir, f'{seed_hash}.svg')

    # Return cached avatar if it exists
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            svg_content = f.read()
        return flask.Response(svg_content, mimetype='image/svg+xml')

    # Fetch from DiceBear API
    dicebear_url = f'https://api.dicebear.com/9.x/bottts-neutral/svg?seed={seed}'
    try:
        response = requests.get(dicebear_url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f'Failed to fetch avatar from DiceBear: {e}')
        return {'error': 'Failed to fetch avatar'}, 500

    svg_content = response.text

    # Cache the avatar
    try:
        with open(cache_file, 'w') as f:
            f.write(svg_content)
    except IOError as e:
        logger.error(f'Failed to cache avatar: {e}')
        # Still return the avatar even if caching fails

    return flask.Response(svg_content, mimetype='image/svg+xml')


@app.route('/api/new_avatar_salt', methods=['POST'])
@login_required
def randomize_avatar():
    avatar_salt = ''.join(random.choice(string.ascii_lowercase) for x in range(8))
    current_user = flask_login.current_user
    current_user.avatar_salt = avatar_salt

    logger.info('Avatar randomized for user %s', current_user.id)

    return flask.jsonify(success=True)