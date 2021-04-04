import flask
import flask_login

import hashlib

from flask_login import login_required
from sqlalchemy.orm import joinedload

from . import app
from . import db
from . import common
from . import models


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

    # TODO: reenable this
    # flask_app.send_mail(flask_mail.Message('Neuer Schoselwetter',
    #                             body=str(user),
    #                             recipients=[app.config['ADMIN_MAIL']]))

    return flask.jsonify(success=True)


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


@app.route('/api/logout', methods=['POST'])
def logout():
    flask_login.logout_user()
    return flask.jsonify(success=True)


@app.route('/api/users')
@login_required
def users_api():
    users = common.query_paying_users()

    scoreboards = {challenge: challenge.calculate_scoreboard(users) for challenge in models.Challenge}

    user_entries = [apify_user(user,
                               scoreboards,
                               include_public_bets=True,
                               include_champion=True,
                               include_scores=True)
                    for user in users]

    return flask.jsonify(user_entries)


@app.route('/api/matches')
@login_required
def matches_api():
    def apify_matches(matches, user_bets_by_match_id):
        matches_entries = []
        for match in matches:
            match_entry = apify_match(match)

            user_bet_for_match = user_bets_by_match_id[match.id]

            match_entry['private_bet'] = apify_bet(user_bet_for_match)
            matches_entries.append(match_entry)

        return matches_entries

    current_user = flask_login.current_user

    user_bets = current_user.bets

    user_bets_by_match_id = {user_bet.match_id: user_bet for user_bet in user_bets}

    # TODO: This is not sufficient
    matches = models.Match.query \
        .options(joinedload(models.Match.team1)) \
        .options(joinedload(models.Match.team2)) \
        .all()

    live_matches = [match for match in matches if match.status == models.Status.LIVE]
    live_matches_entries = apify_matches(live_matches, user_bets_by_match_id)
    over_matches = [match for match in matches if match.status == models.Status.OVER]
    over_matches_entries = apify_matches(over_matches, user_bets_by_match_id)
    scheduled_matches_entries = [apify_match(match) for match in matches if match.status == models.Status.SCHEDULED]

    d = {'live': live_matches_entries,
         'over': over_matches_entries,
         'scheduled': scheduled_matches_entries}

    return flask.jsonify(d)



@app.route('/api/challenge/<int:challenge_id>')
@login_required
def challenge_api(challenge_id):
    try:
        challenge = models.Challenge(challenge_id)
    except ValueError:
        flask.abort(404)

    users = common.query_paying_users()

    scoreboards = {challenge: challenge.calculate_scoreboard(users) for challenge in models.Challenge}

    d = apify_challenge(challenge)

    scoreboard = scoreboards[challenge]

    user_entries = []
    for user in users:
        user_entry = apify_user(user, scoreboards)

        scoreboard_entry = scoreboard[user]

        user_entry['score'] = scoreboard_entry.points
        user_entry['rank'] = scoreboard_entry.rank + 1
        user_entry['reward'] = scoreboard_entry.reward
        user_entries.append(user_entry)

    d['users'] = user_entries

    return flask.jsonify(d)


# @app.route('/api/matches/<int:match_id>')
# @login_required
# def match_api(match_id):
#    try:
#        match = models.Match.query \
#            .options(joinedload(models.Match.bets).joinedload(models.Bet.user)) \
#            .options(joinedload(models.Match.team1)) \
#            .options(joinedload(models.Match.team2)) \
#            .filter_by(id=match_id).one()
#    except sqlalchemy.orm.exc.NoResultFound:
#        flask.abort(404)
#
#    matches_json = flask.jsonify(match.apify(bets=True))
#
#    return matches_json


# @app.route('/api/users/<int:user_id>')
# @login_required
# def user_api(user_id):
#    user = models.User.query \
#        .options(joinedload(models.User.bets).joinedload(models.Bet.match).joinedload(models.Match.team1)) \
#        .options(joinedload(models.User.bets).joinedload(models.Bet.match).joinedload(models.Match.team2)) \
#        .options(joinedload(models.User.expert_team)) \
#        .filter_by(id=user_id) \
#        .one_or_none()
#
#    if user is None:
#        flask.abort(404)
#
#    user_json = flask.jsonify(user.apify(bets=True))
#
#    return user_json


# @app.route('/api/bets')
# @login_required
# def bets_api():
#     current_user = flask_login.current_user
#
#     bets = models.Bet.query.filter_by(user_id=current_user.id) \
#         .options(
#         joinedload(models.Bet.match).
#             joinedload(models.Match.team1)) \
#         .options(
#         joinedload(models.Bet.match).
#             joinedload(models.Match.team2)) \
#         .all()
#
#     bets_json = flask.jsonify([bet.apify(match=True) for bet in bets])
#
#     return bets_json


@app.route('/api/bets/<int:match_id>', methods=['POST'])
@login_required
def bet_api(match_id):
    bet_schema = {
        'type': 'object',
        'properties': {
            'outcome': {'type': 'string', 'enum': [outcome.value for outcome in models.Outcome]},
            'superbet': {'type': 'boolean'}
        },
        'required': ['outcome', 'superbet']}

    posted_bet = flask.request.get_json()

    validation_result = common.validate(posted_bet, bet_schema)
    if validation_result is not None:
        return validation_result

    current_user = flask_login.current_user

    # TODO: joinedload match
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
    bet.superbet = posted_bet['superbet']

    num_supertips = sum([bet.supertip for bet in current_user.bets])

    # Check if supertips are available
    if num_supertips > models.User.MAX_SUPERBETS:
        # TODO: doesn't abort always cause a rollback?
        db.rollback()
        flask.abort(418)

    # Update supertip count in user
    current_user.supertips = num_supertips

    num_users = models.User.query \
        .filter(models.User.paid) \
        .count()

    bet.match.compute_odds(num_users)

    return flask.jsonify(success=True)


@app.route('/api/champion', methods=['POST'])
@login_required
def champion_api():
    champion_schema = {
        'type': 'object',
        'properties': {
            'champion_id': {'type': 'integer'}
        },
        'required': ['champion_id']}

    posted_champion = flask.request.get_json()

    validation_result = common.validate(posted_champion, champion_schema)
    if validation_result is not None:
        return validation_result

    current_user = flask_login.current_user

    if not common.is_before_tournament_start():
        flask.abort(403)

    champion_id = posted_champion['champion_id']

    teams = models.Team.query.options(joinedload(models.Team.users)).all()

    try:
        current_user.champion = next(team for team in teams if team.id == champion_id)
    except StopIteration:
        flask.abort(404)

    users = common.query_paying_users()

    num_players = len(users)

    for team in teams:
        team.compute_odds(num_players)

    return flask.jsonify(success=True)


@app.route('/api/status')
@login_required
def status_api():
    current_user = flask_login.current_user

    users = common.query_paying_users()

    scoreboards = {challenge: challenge.calculate_scoreboard(users) for challenge in models.Challenge}

    teams = models.Team.query.order_by(models.Team.name)
    groups = sorted(list({team.group for team in teams}))

    matches = models.Match.query
    stages = sorted(list({match.stage for match in matches}))

    s = {'stages': stages,
         'groups': groups,
         'user': apify_user(current_user,
                            scoreboards,
                            include_private_bets=True,
                            include_champion=True,
                            include_scores=True),
         'teams': [apify_team(team) for team in teams],
         'champion_editable': common.is_before_tournament_start()}

    return flask.jsonify(s)


def apify_user(user,
               scoreboards,
               include_public_bets=False,
               include_private_bets=False,
               include_champion=False,
               include_scores=False):

    def apify_matches_with_bets(bets):
        matches_with_bets = []
        for bet in bets:
            match_entry = apify_match(bet.match)
            match_entry['bet'] = apify_bet(bet)
            matches_with_bets.append(match_entry)
        return matches_with_bets

    d = {'admin': user.admin,
         'avatar': 'https://api.hello-avatar.com/adorables/400/' + user.name,
         'user_id': user.id,
         'name': user.name,
         'paid': user.paid,
         'reward': sum([scoreboards[challenge][user].reward for challenge in models.Challenge]),
         'visible_superbets': user.supertips}

    if include_champion:
        d['champion'] = apify_team(user.champion) if user.champion is not None else None
        d['champion_correct'] = user.champion_correct

    if include_public_bets:
        d['public_bets'] = apify_matches_with_bets(user.visible_bets)

    if include_private_bets:
        d['private_bets'] = apify_matches_with_bets(user.bets)

    if include_scores:

        scores = []
        for challenge in models.Challenge:
            challenge_entry = apify_challenge(challenge)

            scoreboard_entry = scoreboards[challenge][user]

            challenge_entry['points'] = scoreboard_entry.points
            challenge_entry['rank'] = scoreboard_entry.rank
            challenge_entry['reward'] = scoreboard_entry.reward
            scores.append(challenge_entry)

        d['scores'] = scores

    return d


def apify_team(team):
    return {'team_id': team.id,
            'name': team.name,
            'short_name': team.short_name,
            'group': team.group,
            'champion': team.champion,
            'odds': team.odds}


def apify_match(match):
    d = {'match_id': match.id,
         'date': match.date.isoformat() + 'Z',
         'status': match.status.value,
         'outcome': match.outcome.value if match.outcome is not None else None,
         'team1_name': match.team1.name,
         'team1_iso': match.team1.short_name,
         'team1_goals': match.goals_team1,
         'team2_name': match.team2.name,
         'team2_iso': match.team2.short_name,
         'team2_goals': match.goals_team2,
         'stage': match.stage}

    if not match.editable:
        d['odds'] = {models.Outcome.TEAM1_WIN.value: match.odds[models.Outcome.TEAM1_WIN],
                     models.Outcome.TEAM2_WIN.value: match.odds[models.Outcome.TEAM2_WIN],
                     models.Outcome.DRAW.value: match.odds[models.Outcome.DRAW]}

    return d


def apify_bet(bet):
    d = {'outcome': bet.outcome.value if bet.outcome is not None else None,
         'superbet': bet.supertip}

    points_by_challenge = bet.points()

    challenges = []
    for challenge, points in points_by_challenge.items():
        challenge_entry = apify_challenge(challenge)
        challenge_entry['points'] = points

        challenges.append(challenge_entry)

    d['points'] = challenges

    return d


def apify_challenge(challenge):
    return {'challenge_id': challenge.value,
            'name': challenge.name}
