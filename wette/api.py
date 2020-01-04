import flask
import flask_login
import sqlalchemy

import hashlib
import jsonschema

from flask_login import login_required
from sqlalchemy.orm import joinedload

import flask_app
import models

from flask_app import app

login_schema = {
        'type': 'object',
        'properties': {
            'email': {'type': 'string'},
            'password': {'type': 'string'},
            'rememberme': {'type': 'boolean'}
            },
        'required': ['email', 'password']}


def validate(post, schema):

    try:
        jsonschema.validate(post, schema=schema)
    except (jsonschema.ValidationError, jsonschema.SchemaError) as e:

        errors = list(jsonschema.Draft7Validator(schema).iter_errors(post))

        errors = [e.message for e in errors]

        return flask.jsonify(errors=errors), 400

    return None


@app.route('/api/v1/login', methods=['POST'])
def login():

    posted_login = flask.request.get_json()

    validation_result = validate(posted_login, login_schema)
    if validation_result is not None: return validation_result

    salted_password = bytes(app.config['PASSWORD_SALT'] + posted_login['password'], 'utf-8')
    password_hash = hashlib.md5(salted_password).hexdigest()

    q = flask_app.db.session.query(models.User).filter(
        models.User.email == posted_login['email'],
        models.User.password == password_hash)

    user = q.first()

    if user is not None:

        if 'remember' in posted_login:
            remember = posted_login['remember']
        else:
            remember = False

        flask_login.login_user(user, remember=remember)

        return flask.jsonify(sucess=True)

    return flask.jsonify(errors=["Incorrect credentials"]), 401

@app.route('/api/v1/logout', methods=['POST'])
def logout():
    flask_login.logout_user()
    return flask.jsonify(sucess=True)


@app.route('/api/v1/matches')
@login_required
def matches_api():

    matches = flask_app.db_session.query(models.Match) \
        .options(joinedload(models.Match.team1)) \
        .options(joinedload(models.Match.team2)) \
        .all()

    matches_json = flask.jsonify([match.apify(users) for match in matches])

    return matches_json


@app.route('/api/v1/matches/<int:match_id>')
@login_required
def match_api(match_id):

    try:
        match = flask_app.db_session.query(models.Match) \
        .options(joinedload(models.Match.bets).joinedload(models.Bet.user)) \
        .options(joinedload(models.Match.team1)) \
        .options(joinedload(models.Match.team2)) \
        .filter(models.Match.id == match_id).one()
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
@login_required
def users_api():

    # TODO: Duplicate code
    users = flask_app.db_session.query(models.User) \
        .options(joinedload(models.User.expert_team)) \
        .options(joinedload(models.User.champion)) \
        .filter(models.User.paid) \
        .order_by(models.User.points.desc()) \
        .all()

    users_json = flask.jsonify([user.apify(users=users) for user in users])

    return users_json


@app.route('/api/v1/users/<int:user_id>')
@login_required
def user_api(user_id):

    user = flask_app.db_session.query(models.User) \
        .options(joinedload(models.User.bets).joinedload(models.Bet.match).joinedload(models.Match.team1)) \
        .options(joinedload(models.User.bets).joinedload(models.Bet.match).joinedload(models.Match.team2)) \
        .options(joinedload(models.User.expert_team)) \
        .filter(models.User.id == user_id) \
        .one_or_none()

    if user is None:
        flask.abort(404)

    users = flask_app.db_session.query(models.User) \
        .options(joinedload(models.User.expert_team)) \
        .filter(models.User.paid) \
        .all()

    user_json = flask.jsonify(user.apify(bets=True, users=users))

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


betSchema = {
    'outcome': {'type': 'string', 'oneOf': [outcome.value for outcome in models.Outcome]},
    'supertip': 'boolean'
}



@app.route('/api/v1/bets/<int:match_id>', methods=['POST'])
@login_required
def bet_api(match_id):

#    inputs = BetPost(flask.request)
#
#    if not inputs.validate():
#        return flask.jsonify(success=False, errors=inputs.errors)

    current_user = flask_login.current_user

    bet = flask_app.db_session.query(models.Bet) \
        .filter(models.Bet.user_id == current_user.id) \
        .filter(models.Bet.match_id == match_id).one_or_none()

    if bet is None:
        flask.abort(404)

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

    # Update supertip count in user
    current_user.supertips = num_supertips

    return flask.jsonify(bet.apify())

@app.route('/api/v1/champion', methods=['POST'])
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

    # TODO: Duplicate code
    users = flask_app.db_session.query(models.User) \
        .filter(models.User.paid) \
        .all()

    s = {}
    s['stages'] = [stage.value for stage in models.Stage]
    s['groups'] = groups
    s['user'] = current_user.apify(show_private=True, users=users)
    s['teams'] = [team.apify() for team in teams]
    s['champion_editable'] = current_user.champion_editable

    return flask.jsonify(s)
