from datetime import datetime, timezone

import flask
import flask_mail
import jsonschema
import sqlalchemy as sa

from sqlalchemy.orm import joinedload

from . import db
from . import mail
from . import models


def send_mail(subject, body, recipients):

    msg = flask_mail.Message(subject=subject, body=body, recipients=recipients)

    try:
        msg.sender = 'info@schosel.net'
        mail.send(msg)
    except Exception:
        print('Tried to send mail, did not work.')
        print(msg)
    print('Message sent successfully.')


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

        errors = [e.message for e in errors]

        return flask.jsonify(errors=errors), 400

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
