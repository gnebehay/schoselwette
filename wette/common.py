from datetime import datetime

import flask
import flask_mail
import jsonschema

from sqlalchemy.orm import joinedload

from . import models
from . import mail


def send_mail_template(tpl, recipients, **kwargs):
    rendered_mail = flask.render_template('mail/' + tpl, **kwargs)
    subject = rendered_mail.splitlines()[0]
    body = '\n'.join(rendered_mail.splitlines()[1:])

    msg = flask_mail.Message(subject=subject, body=body, recipients=recipients)

    try:
        msg.sender = 'info@schosel.net'
        mail.send(msg)
    except:
        print('Tried to send mail, did not work.')
        print(msg)


def validate(post, schema):
    try:
        jsonschema.validate(post, schema=schema)
    except (jsonschema.ValidationError, jsonschema.SchemaError) as e:

        errors = list(jsonschema.Draft7Validator(schema).iter_errors(post))

        errors = [e.message for e in errors]

        return flask.jsonify(errors=errors), 400

    return None


def query_paying_users():
    users = models.User.query \
        .options(joinedload(models.User.champion)) \
        .filter(models.User.paid) \
        .all()
    return users


def query_teams():
    teams = models.Team.query \
        .all()
    return teams


def is_before_tournament_start():

    # TODO: Tom, remove next line
    # return True


    first_match = models.Match.query.order_by('date').first()

    if first_match is None:
        return True

    return first_match.date > datetime.utcnow()


