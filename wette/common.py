from datetime import datetime

import flask
import jsonschema

from sqlalchemy.orm import joinedload

from . import models

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


def is_before_tournament_start():
    first_match = models.Match.query.order_by('date').first()

    if first_match is None:
        return True

    return first_match.date > datetime.utcnow()


