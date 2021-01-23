import datetime

import flask
import flask_login
import sqlalchemy

import hashlib
import jsonschema

from flask_login import login_required
from sqlalchemy.orm import joinedload

import flask_app
import models
import apification

from flask_app import app


def champion_editable():
    first_match = models.Match.query.order_by('date').first()
    return first_match.date > datetime.datetime.utcnow()


## TODO: This seems not to be used for anything anyway
## TODO: Why is this a property of user?
#@property
#def final_started(self):
#    # TODO TODO TODO: Needs to be fixed
#    return False
#    final_match = flask_app.db.query(Match).filter(Match.stage == Stage.FINAL).one_or_none()
#
#    if final_match is None:
#        return False
#    return final_match.date < datetime.datetime.utcnow()


def validate(post, schema):

    try:
        jsonschema.validate(post, schema=schema)
    except (jsonschema.ValidationError, jsonschema.SchemaError) as e:

        errors = list(jsonschema.Draft7Validator(schema).iter_errors(post))

        errors = [e.message for e in errors]

        return flask.jsonify(errors=errors), 400

    return None

register_schema = {
        'type': 'object',
        'properties': {
            'email': {'type': 'string'},
            'password': {'type': 'string', 'minLength': 8},
            'firstName': {'type': 'string'},
            'lastName': {'type': 'string'}
            },
        'required': ['email', 'password', 'firstName', 'lastName']}

@app.route('/api/v1/register', methods=['POST'])
def register():

    posted_login = flask.request.get_json()

    validation_result = validate(posted_login, login_schema)
    if validation_result is not None: return validation_result

    user = models.User()
    user.email = posted_login['email']
    user.email_hash = hashlib.md5(bytes(user.email, 'utf-8')).hexdigest()
    user.first_name = posted_login['firstName']
    user.last_name = posted_login['lastName']
    user.paid = False

    salted_password = bytes(app.config['PASSWORD_SALT'] + posted_login['password'], 'utf-8')
    user.password = hashlib.md5(salted_password).hexdigest()

    flask_app.db.session.add(user)

    user.create_missing_bets()

    flask_app.send_mail_template('welcome.eml', recipients=[user.email], user=user)

    # TODO: reenable this
    #flask_app.send_mail(flask_mail.Message('Neuer Schoselwetter',
    #                             body=str(user),
    #                             recipients=[app.config['ADMIN_MAIL']]))

    return flask.jsonify(success=True)


login_schema = {
        'type': 'object',
        'properties': {
            'email': {'type': 'string'},
            'password': {'type': 'string'},
            'rememberme': {'type': 'boolean'}
            },
        'required': ['email', 'password']}

@app.route('/api/v1/login', methods=['POST'])
def login():

    posted_login = flask.request.get_json()

    validation_result = validate(posted_login, login_schema)
    if validation_result is not None: return validation_result

    salted_password = bytes(app.config['PASSWORD_SALT'] + posted_login['password'], 'utf-8')
    password_hash = hashlib.md5(salted_password).hexdigest()

    q = models.User.query.filter_by(email=posted_login['email'], password=password_hash)

    user = q.first()

    if user is not None:

        if 'remember' in posted_login:
            remember = posted_login['remember']
        else:
            remember = False

        flask_login.login_user(user, remember=remember)

        return flask.jsonify(success=True)

    return flask.jsonify(errors=["Oops, wrong login data."]), 401

@app.route('/api/v1/logout', methods=['POST'])
def logout():
    flask_login.logout_user()
    return flask.jsonify(success=True)

@app.route('/api/v1/users')
@login_required
def users_api():

    users = models.User.query \
        .options(joinedload(models.User.champion)) \
        .filter(models.User.paid) \
        .all()

    user_entries = []
    for user in users:

        user_entry = apification.apify_user(user)

        public_bets = []
        for bet in user.visible_bets:

            # Start with the match as a base
            public_bet_entry = apification.apify_match(bet.match)

            bet_entry = apification.apify_bet(bet)

            points_by_challenge = bet.points()

            challenges = []
            for challenge, points in points_by_challenge.items():
                challenge_entry = apification.apify_challenge(challenge)
                challenge_entry['points'] = points

                challenges.append(challenge_entry)

            bet_entry['points'] = challenges
            public_bet_entry['bet'] = bet_entry

            public_bets.append(public_bet_entry)

        user_entry['public_bets'] = public_bets

        scores = []

        for challenge in models.Challenge:
            challenge_entry = apification.apify_challenge(challenge)

            user_points_for_challenge = user.points_for_challenge(challenge)
            ranking = sorted([other_user.points_for_challenge(challenge) for other_user in users], reverse=True)

            challenge_entry['points'] = user_points_for_challenge
            challenge_entry['rank'] = ranking.index(user_points_for_challenge) + 1

            scores.append(challenge_entry)

        user_entry['scores'] = scores

        user_entries.append(user_entry)

    return flask.jsonify(user_entries)

@app.route('/api/v1/matches')
@login_required
def matches_api():

    matches = models.Match.query \
        .options(joinedload(models.Match.team1)) \
        .options(joinedload(models.Match.team2)) \
        .all()

    matches_json = flask.jsonify([match.apify() for match in matches])

    return matches_json


@app.route('/api/v1/matches/<int:match_id>')
@login_required
def match_api(match_id):

    try:
        match = models.Match.query \
        .options(joinedload(models.Match.bets).joinedload(models.Bet.user)) \
        .options(joinedload(models.Match.team1)) \
        .options(joinedload(models.Match.team2)) \
        .filter_by(id=match_id).one()
    except sqlalchemy.orm.exc.NoResultFound:
        flask.abort(404)

    matches_json = flask.jsonify(match.apify(bets=True))

    return matches_json




@app.route('/api/v1/users/<int:user_id>')
@login_required
def user_api(user_id):

    user = models.User.query \
        .options(joinedload(models.User.bets).joinedload(models.Bet.match).joinedload(models.Match.team1)) \
        .options(joinedload(models.User.bets).joinedload(models.Bet.match).joinedload(models.Match.team2)) \
        .options(joinedload(models.User.expert_team)) \
        .filter_by(id=user_id) \
        .one_or_none()

    if user is None:
        flask.abort(404)

    user_json = flask.jsonify(user.apify(bets=True))

    return user_json


@app.route('/api/v1/bets')
@login_required
def bets_api():

    current_user = flask_login.current_user

    bets = models.Bet.query.filter_by(user_id=current_user.id) \
        .options(
                joinedload(models.Bet.match).
                joinedload(models.Match.team1)) \
        .options(
                joinedload(models.Bet.match).
                joinedload(models.Match.team2)) \
        .all()

    bets_json = flask.jsonify([bet.apify(match=True) for bet in bets])

    return bets_json


bet_schema = {
    'type': 'object',
    'properties': {
        'outcome': {'type': 'string', 'enum': [outcome.value for outcome in models.Outcome]},
        'supertip': {'type': 'boolean'}
    },
    'required': ['outcome', 'supertip']}


@app.route('/api/v1/bets/<int:match_id>', methods=['POST'])
@login_required
def bet_api(match_id):

    posted_bet = flask.request.get_json()

    validation_result = validate(posted_bet, bet_schema)
    if validation_result is not None: return validation_result

    current_user = flask_login.current_user

    bet = models.Bet.query \
        .filter_by(user_id=current_user.id, match_id=match_id) \
        .one_or_none()

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
    if num_supertips > models.User.MAX_SUPERBETS:
        flask_app.db.rollback()
        flask.abort(418)

    # Update supertip count in user
    current_user.supertips = num_supertips

    return flask.jsonify(bet.apify())


champion_schema = {
    'type': 'object',
    'properties': {
        'champion_id': {'type': 'integer'}
    },
    'required': ['champion_id']}

@app.route('/api/v1/champion', methods=['POST'])
@login_required
def champion_api():

    posted_champion = flask.request.get_json()

    validation_result = validate(posted_champion, champion_schema)
    if validation_result is not None: return validation_result

    current_user = flask_login.current_user

    if not current_user.champion_editable:
        flask.abort(403)

    posted_champion = flask.request.get_json()

    champion_id = posted_champion['champion_id']

    champion = models.Team.query.filter_by(id=champion_id).one_or_none()

    current_user.champion_id = champion_id
    current_user.champion = champion

    return flask.jsonify(current_user.apify(show_private=True))



@app.route('/api/v1/status')
@login_required
def status_api():

    current_user = flask_login.current_user

    teams = models.Team.query.order_by(models.Team.name)
    groups = sorted(list({team.group for team in teams}))

    s = {}
    s['stages'] = 'tbd'
    s['groups'] = groups
    s['user'] = current_user.apify(show_private=True)
    s['teams'] = [team.apify() for team in teams]
    s['champion_editable'] = current_user.champion_editable

    return flask.jsonify(s)
