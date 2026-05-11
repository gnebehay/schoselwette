from datetime import datetime, timezone

import logging

import flask
import flask_mail
import jsonschema
import sqlalchemy as sa

from sqlalchemy.orm import joinedload

from . import db
from . import mail
from . import models


logger = logging.getLogger(__name__)

def send_mail(subject, body, recipients):

    msg = flask_mail.Message(subject=subject, body=body, recipients=recipients)

    try:
        msg.sender = 'info@schosel.net'
        mail.send(msg)
        logger.info('Message sent successfully.')
    except Exception:
        logger.exception('Tried to send mail, did not work.')
        logger.debug(msg)


def send_mail_template(tpl, recipients, **kwargs):
    rendered_mail = flask.render_template('mail/' + tpl, **kwargs)
    subject = rendered_mail.splitlines()[0]
    body = '\n'.join(rendered_mail.splitlines()[1:])

    send_mail(subject=subject, body=body, recipients=recipients)


def validate(post, schema):
    try:
        jsonschema.validate(post, schema=schema)
    except (jsonschema.ValidationError, jsonschema.SchemaError) as e:

        errors = list(jsonschema.Draft7Validator(schema).iter_errors(post))

        for e in errors:
            field = ".".join(str(x) for x in e.path) or "<root>"
            logger.info(f'Validation errors: "field={field} rule={e.validator}"')

        error_messages = [e.message for e in errors]

        return flask.jsonify(errors=error_messages), 400

    return None


def query_paying_users():
    users = db.session.execute(
        sa.select(models.User)
        .options(joinedload(models.User.champion))
        .where(models.User.paid)
    ).scalars().all()
    return users


def is_before_tournament_start():
    first_match = db.session.execute(
        sa.select(models.Match).order_by(models.Match.date)
    ).scalar()

    if first_match is None:
        return True

    return first_match.date > datetime.now(timezone.utc).replace(tzinfo=None)