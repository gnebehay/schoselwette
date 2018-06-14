import flask
import flask_inputs
import flask_login
import sqlalchemy

from flask_login import login_required
from flask_inputs.validators import JsonSchema
from sqlalchemy.orm import joinedload

import flask_app
import models

from flask_app import app


@app.route('/api/v1/matches')
@login_required
def matches_api():

    users = flask_app.db_session.query(models.User).filter(models.User.paid) \
        .options(
                joinedload(models.User.bets).
                joinedload(models.Bet.match).
                joinedload(models.Match.team1)) \
        .options(
                joinedload(models.User.bets).
                joinedload(models.Bet.match).
                joinedload(models.Match.team2)) \
        .all()

    # TODO: Check eager loading
    matches = flask_app.db_session.query(models.Match)

    matches_json = flask.jsonify([match.apify(users) for match in matches])

    return matches_json


@app.route('/api/v1/matches/<int:match_id>')
def match_api(match_id):

    try:
        match = flask_app.db_session.query(models.Match).filter(models.Match.id == match_id).one()
    except sqlalchemy.orm.exc.NoResultFound:
        flask.abort(404)

    users = flask_app.db_session.query(models.User).filter(models.User.paid) \
        .options(
                joinedload(models.User.bets).
                joinedload(models.Bet.match).
                joinedload(models.Match.team1)) \
        .options(
                joinedload(models.User.bets).
                joinedload(models.Bet.match).
                joinedload(models.Match.team2)) \
        .all()

    matches_json = flask.jsonify(match.apify(users, bets=True))

    return matches_json


@app.route('/api/v1/users')
def users_api():

    return ""

    users = flask_app.db_session.query(models.User).filter(models.User.paid) \
        .options(
                joinedload(models.User.bets).
                joinedload(models.Bet.match).
                joinedload(models.Match.team1)) \
        .options(
                joinedload(models.User.bets).
                joinedload(models.Bet.match).
                joinedload(models.Match.team2)) \
        .all()

    users_sorted = sorted(users, key=lambda user: user.points(users), reverse=True)

    users_json = flask.jsonify([user.apify(users) for user in users_sorted])

    return users_json


@app.route('/api/v1/users/<int:user_id>')
def user_api(user_id):

    users = flask_app.db_session.query(models.User).filter(models.User.paid) \
        .options(
                joinedload(models.User.bets).
                joinedload(models.Bet.match).
                joinedload(models.Match.team1)) \
        .options(
                joinedload(models.User.bets).
                joinedload(models.Bet.match).
                joinedload(models.Match.team2)) \
        .all()

    try:
        user = next(u for u in users if u.id == user_id)
    except StopIteration:
        flask.abort(404)

    user_json = flask.jsonify(user.apify(users, bets=True))

    return user_json


@app.route('/api/v1/bets')
@login_required
def bets_api():

    current_user = flask_login.current_user

    users = flask_app.db_session.query(models.User).filter(models.User.paid) \
        .options(
                joinedload(models.User.bets).
                joinedload(models.Bet.match).
                joinedload(models.Match.team1)) \
        .options(
                joinedload(models.User.bets).
                joinedload(models.Bet.match).
                joinedload(models.Match.team2)) \
        .all()

    bets = flask_app.db_session.query(models.Bet) \
        .filter(models.Bet.user_id == current_user.id) \
        .options(
                joinedload(models.Bet.match).
                joinedload(models.Match.team1)) \
        .options(
                joinedload(models.Bet.match).
                joinedload(models.Match.team2)) \
        .all()

    bets_json = flask.jsonify([bet.apify(users, match=True) for bet in bets])

    return bets_json




schema = {
    'outcome': {'type': 'string', 'oneOf': [outcome.value for outcome in models.Outcome]},
    'supertip': 'boolean'
}


class JsonInputs(flask_inputs.Inputs):
    json = [JsonSchema(schema=schema)]


@app.route('/api/v1/bets/<int:match_id>', methods=['POST'])
@flask_app.csrf.exempt
@login_required
def bet_api(match_id):

    inputs = JsonInputs(flask.request)

    if not inputs.validate():
        return flask.jsonify(success=False, errors=inputs.errors)

    current_user = flask_login.current_user


    bets = [bet for bet in current_user.bets if bet.match.id == match_id]

    if not bets:
        flask.abort(404)

    bet = bets[0]

    if not bet.match.editable:
        flask.abort(403)

    posted_bet = flask.request.get_json()

    posted_outcome = posted_bet['outcome']
    if posted_outcome:
        bet.outcome = models.Outcome(posted_outcome)
    bet.supertip = posted_bet['supertip']
    
    num_supertips = sum([bet.supertip for bet in current_user.bets])

    # Check if supertips are available
    if num_supertips > models.User.MAX_SUPERTIPS:
        flask_app.db_session.rollback()
        flask.abort(418)

    users = flask_app.db_session.query(models.User).filter(models.User.paid) \
        .options(
                joinedload(models.User.bets).
                joinedload(models.Bet.match).
                joinedload(models.Match.team1)) \
        .options(
                joinedload(models.User.bets).
                joinedload(models.Bet.match).
                joinedload(models.Match.team2)) \
        .all()

    return flask.jsonify(bet.apify(users))

@app.route('/api/v1/champion', methods=['POST'])
@flask_app.csrf.exempt
@login_required
def champion_api():

    current_user = flask_login.current_user

    if not current_user.champion_editable:
        flask.abort(403)

    posted_champion = flask.request.get_json()

    champion_id = posted_champion['champion_id']

    champion = flask_app.db_session.query(models.Team).filter(models.Team.id == champion_id).one_or_none()

    current_user.champion_id = champion_id
    current_user.champion = champion

    return flask.jsonify(current_user.apify(show_private=True))



@app.route('/api/v1/status')
@login_required
def status_api():

    users = flask_app.db_session.query(models.User).filter(models.User.paid) \
        .options(
                joinedload(models.User.bets).
                joinedload(models.Bet.match).
                joinedload(models.Match.team1)) \
        .options(
                joinedload(models.User.bets).
                joinedload(models.Bet.match).
                joinedload(models.Match.team2)) \
        .all()

    current_user = flask_login.current_user

    teams = flask_app.db_session.query(models.Team).order_by(models.Team.name)
    groups = sorted(list({team.group for team in teams}))

    s = {}
    s['stages'] = [stage.value for stage in models.Stage]
    s['groups'] = groups
    s['user'] = current_user.apify(users, show_private=True)
    s['teams'] = [team.apify() for team in teams]
    s['champion_editable'] = current_user.champion_editable

    return flask.jsonify(s)
