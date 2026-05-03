from datetime import datetime
from datetime import timezone

import random
import string

import flask
import flask_login
import sqlalchemy as sa

from flask_login import login_required

from . import app
from . import common
from . import db
from . import models


@app.route('/api/admin/confirm_payment/<int:user_id>', methods=['POST'])
@login_required
def confirm_payment(user_id):

    if not flask_login.current_user.admin:
        flask.abort(403)

    if not common.is_before_tournament_start():
        flask.abort(403)

    user = db.session.execute(
        sa.select(models.User).filter_by(id=user_id)
    ).scalar_one()

    user.paid = True

    # Now all odds have to be recomputed
    # But not the points of the players, because we don't allow registration after the first match starts
    num_players = db.session.execute(
        sa.select(sa.func.count()).select_from(models.User).where(models.User.paid)
    ).scalar()
    matches = db.session.execute(sa.select(models.Match)).scalars().all()

    for match in matches:
        match.compute_odds(num_players)

    common.send_mail_template('payment_confirmed.eml', recipients=[user.email], user=user)

    return flask.jsonify(success=True)


@app.route('/api/admin/match', methods=['POST'])
@login_required
def match():

    if not flask_login.current_user.admin:
        flask.abort(403)

    match_schema = {
        'type': 'object',
        'properties': {
            'team1Name': {'type': 'string'},
            'team2Name': {'type': 'string'},
            'dateTime': {'type': 'string'},
            'stage': {'type': 'string'},
        },
        'required': ['team1Name', 'team2Name', 'dateTime', 'stage']}

    posted_match = flask.request.get_json()

    validation_result = common.validate(posted_match, match_schema)
    if validation_result is not None:
        return validation_result

    process_match(posted_match)

    return flask.jsonify(success=True)


# TODO: This should probably be in a separate module
def process_match(posted_match, fixture=None):

    # Make sure that we store UTC dates
    try:
        match_datetime = datetime.fromisoformat(posted_match['dateTime'])
        if match_datetime.tzinfo is None:
            match_datetime.replace(tzinfo=timezone.utc)
        match_datetime.astimezone(timezone.utc)
    except ValueError as e:
        # TODO: This doesn't make sense if we run this as a one-off CLI job
        flask.abort(400, str(e))
    team1_db = db.session.execute(
        sa.select(models.Team).filter_by(name=posted_match['team1Name'])
    ).scalar_one_or_none()
    team2_db = db.session.execute(
        sa.select(models.Team).filter_by(name=posted_match['team2Name'])
    ).scalar_one_or_none()
    if team1_db is None:
        team1_db = models.Team()
        team1_db.name = posted_match['team1Name']
        team1_db.short_name = ''
        team1_db.group = 'A'
        team1_db.champion = False
        team1_db.odds = 0

        db.session.add(team1_db)
    if team2_db is None:
        team2_db = models.Team()
        team2_db.name = posted_match['team2Name']
        team2_db.short_name = ''
        team2_db.group = 'A'
        team2_db.champion = False
        team2_db.odds = 0

        db.session.add(team2_db)

    posted_stage = posted_match['stage']
    match_db = db.session.execute(
        sa.select(models.Match).where(
            models.Match.team1_id == team1_db.id,
            models.Match.team2_id == team2_db.id,
            models.Match.stage == posted_stage
        )
    ).scalar_one_or_none()
    if match_db is None:
        match_db = models.Match(team1=team1_db, team2=team2_db, stage=posted_stage, date=match_datetime)
        if 'fixture_id' in posted_match:
            match_db.fixture_id = posted_match['fixture_id']
        if fixture is not None:
            match_db.api_data = fixture
        db.session.add(match_db)
        print('Insert: ' + str(match_db))

        all_users = db.session.execute(sa.select(models.User)).scalars().all()


    else:
        print('Match ' + str(match_db) + ' already in database.')

        match_db.date = match_datetime

        if 'fixture_id' in posted_match:
            match_db.fixture_id = posted_match['fixture_id']
        if fixture is not None:
            match_db.api_data = fixture

    for user in all_users:
        print('Creating missing bets for ' + str(user))
        user.create_missing_bets()

        # TODO: Send email to admins here


@app.route('/api/admin/outcome/<int:match_id>', methods=['POST'])
@login_required
def outcome(match_id):

    if not flask_login.current_user.admin:
        flask.abort(403)

    match = db.session.execute(
        sa.select(models.Match).filter_by(id=match_id)
    ).scalar_one_or_none()

    if match is None:
        flask.abort(404)

    outcome_schema = {
        'type': 'object',
        'properties': {
            'goalsTeam1': {'type': 'integer'},
            'goalsTeam2': {'type': 'integer'},
            'firstGoal': {'type': 'string', 'enum': [outcome.value for outcome in models.Outcome]}, # optional
            'over': {'type': 'boolean'},
        },
        'required': ['goalsTeam1', 'goalsTeam2']}

    posted_outcome = flask.request.get_json()

    validation_result = common.validate(posted_outcome, outcome_schema)
    if validation_result is not None:
        return validation_result

    match.goals_team1 = posted_outcome['goalsTeam1']
    match.goals_team2 = posted_outcome['goalsTeam2']

    if 'firstGoal' in posted_outcome:
        match.firstGoal = posted_outcome['firstGoal']

    if 'over' in posted_outcome:
        match.over = posted_outcome['over']

    users = common.query_paying_users()
    for user in users:
        user.compute_points()

    return flask.jsonify(success=True)


@app.route('/api/admin/make_admin/<int:user_id>')
@login_required
def make_admin(user_id):

    if not flask_login.current_user.admin:
        flask.abort(403)

    user = db.session.execute(
        sa.select(models.User).where(models.User.id == user_id)
    ).scalar_one()

    user.admin = True

    return flask.jsonify(success=True)


@app.route('/api/admin/users', methods=['GET'])
@login_required
def users():

    if not flask_login.current_user.admin:
        flask.abort(403)

    all_users = db.session.execute(sa.select(models.User)).scalars().all()

    response = []

    for user in all_users:

        d = {'admin': user.admin,
             'paid': user.paid,
             'user_id': user.id,
             'email': user.email,
             'name': user.first_name + " " + user.last_name}

        response.append(d)

    return flask.jsonify(response)


@app.route('/api/admin/make_champion', methods=['POST'])
@login_required
def make_champion():

    if not flask_login.current_user.admin:
        flask.abort(403)

    schema = {
        'type': 'object',
        'properties': {
            'champion_id': {'type': 'integer'},
        },
        'required': ['champion_id']}

    posted_data = flask.request.get_json()

    validation_result = common.validate(posted_data, schema)
    if validation_result is not None:
        return validation_result

    champion_id = posted_data['champion_id']

    teams = db.session.execute(sa.select(models.Team)).scalars().all()

    for team in teams:
        if team.id == champion_id:
            team.champion = True
        else:
            team.champion = False

    for user in common.query_paying_users():
        user.compute_points()

    return {'success': True}


@login_required
@app.route('/api/admin/recompute', methods=['POST'])
def recompute():

    if not flask_login.current_user.admin:
        flask.abort(403)

    users = common.query_paying_users()
    matches = db.session.execute(sa.select(models.Match)).scalars().all()

    num_players = len(users)

    for match in matches:
        match.compute_odds(num_players)

    for user in users:
        user.compute_points()

    return flask.jsonify(success=True)


@login_required
@app.route('/api/admin/trigger_password_reset/<int:user_id>', methods=['POST'])
def trigger_reset_password(user_id):

    if not flask_login.current_user.admin:
        flask.abort(403)

    user = db.session.execute(
        sa.select(models.User).filter_by(id=user_id)
    ).scalar_one()
    # Reset token is set irrespective of previous value
    user.reset_token = ''.join(random.choice(string.ascii_lowercase) for _ in range(8))

    common.send_mail_template('reset_password.eml', recipients=[user.email], user=user)

    return flask.jsonify(success=True)
