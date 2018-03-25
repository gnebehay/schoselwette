import flask
import flask_inputs
import flask_login
import sqlalchemy

from flask_login import login_required
from flask_inputs.validators import JsonSchema

import flask_app
import models

from flask_app import app


# TODO: No login for the moment
@app.route('/api/v1/matches')
@login_required
def matches_api():

    # TODO: Check eager loading
    matches = flask_app.db_session.query(models.Match)

    matches_json = flask.jsonify([match.apify() for match in matches])

    # TODO: get rid of this
    matches_json.headers['Access-Control-Allow-Origin'] = '*'

    return matches_json


@app.route('/api/v1/matches/<int:match_id>')
def match_api(match_id):

    try:
        match = flask_app.db_session.query(models.Match).filter(models.Match.id == match_id).one()
    except sqlalchemy.orm.exc.NoResultFound:
        flask.abort(404)

    matches_json = flask.jsonify(match.apify(bets=True))

    # TODO: get rid of this
    matches_json.headers['Access-Control-Allow-Origin'] = '*'

    return matches_json


@app.route('/api/v1/users')
def users_api():

    # TODO: Duplicate code
    users = flask_app.db_session.query(models.User).filter(models.User.paid)

    users_sorted = sorted(users, key=lambda x: x.points, reverse=True)

    users_json = flask.jsonify([user.apify() for user in users_sorted])

    # TODO: get rid of this
    users_json.headers['Access-Control-Allow-Origin'] = '*'

    return users_json


@app.route('/api/v1/users/<int:user_id>')
def user_api(user_id):

    try:
        user = flask_app.db_session.query(models.User).filter(models.User.id == user_id).one()
    except sqlalchemy.orm.exc.NoResultFound:
        flask.abort(404)

    user_json = flask.jsonify(user.apify(bets=True))

    # TODO: get rid of this
    user_json.headers['Access-Control-Allow-Origin'] = '*'

    return user_json


@app.route('/api/v1/bets')
@login_required
def bets_api():

    current_user = flask_login.current_user

    bets_json = flask.jsonify([bet.apify(match=True) for bet in current_user.visible_bets])

    return bets_json




schema = {
    'outcome': {'oneOf': [outcome.value for outcome in models.Outcome]},
    'supertip': 'boolean'
}


class JsonInputs(flask_inputs.Inputs):
    json = [JsonSchema(schema=schema)]


@app.route('/api/v1/bets/<int:match_id>', methods=['POST'])
@login_required
def bet_api(match_id):

    inputs = JsonInputs(flask.request)

    if not inputs.validate():
        return flask.jsonify(success=False, errors=inputs.errors)

    # TODO: Supertips...

    # outcome_value = flask.request.form['outcome']
    #
    # try:
    #     outcome = models.Outcome(outcome_value)
    # except ValueError:
    #     flask.abort(400)
    #
    current_user = flask_login.current_user

    bets = [bet for bet in current_user.bets if bet.match.id == match_id]

    if not bets:
        flask.abort(404)

    bet = bets[0]

    if not bet.match.editable:
        flask.abort(403)

    bet.outcome = outcome

    # TODO: Check if supertips are available

    return flask.jsonify(bet.apify())



@app.route('/api/v1/status')
@login_required
def status_api():

    current_user = flask_login.current_user

    teams = flask_app.db_session.query(models.Team)
    groups = sorted(list({team.group for team in teams}))

    s = {}
    s['stages'] = [stage.value for stage in models.Stage]
    s['groups'] = groups
    s['user'] = current_user.apify(show_private=True)

    return flask.jsonify(s)





    """

    {
      "stages": [
	"Group stage",
	"Round of 16",
	"Quarter-finals",
	"Semi-finals",
	"Final"
      ],
      "groups": [
	"A",
	"B",
	"C"
      ],
      "num_users": 42
    }
    """
