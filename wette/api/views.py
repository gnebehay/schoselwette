import logging

import flask
import flask_login
import sqlalchemy as sa

from flask_login import login_required
from sqlalchemy.orm import joinedload
from urllib.parse import quote

from .. import app
from .. import db
from .. import common
from .. import models


logger = logging.getLogger(__name__)


@app.route('/api/users')
@login_required
def users_api():

    users = db.session.execute(
        sa.select(models.User)
        .options(joinedload(models.User.champion))
        .options(joinedload(models.User.bets).joinedload(models.Bet.match).joinedload(models.Match.team1))
        .options(joinedload(models.User.bets).joinedload(models.Bet.match).joinedload(models.Match.team2))
        .where(models.User.paid)
    ).scalars().unique().all()

    scoreboards = {challenge: challenge.calculate_scoreboard(users) for challenge in models.Challenge}

    include_champion = not common.is_before_tournament_start()

    user_entries = [apify_user(user,
                               scoreboards,
                               include_public_bets=True,
                               include_champion=include_champion,
                               include_scores=True)
                    for user in users]

    return flask.jsonify(sorted(user_entries, key=lambda user_entry: (user_entry['reward'], user_entry['name'])))


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

    matches = db.session.execute(
        sa.select(models.Match)
        .options(joinedload(models.Match.team1))
        .options(joinedload(models.Match.team2))
    ).scalars().unique().all()

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

        scoreboard_entry = scoreboard[user.id]

        user_entry['score'] = scoreboard_entry.points
        user_entry['rank'] = scoreboard_entry.rank + 1
        user_entry['reward'] = scoreboard_entry.reward
        user_entries.append(user_entry)

    d['users'] = user_entries

    return flask.jsonify(d)


@app.route('/api/status')
@login_required
def status_api():
    current_user = flask_login.current_user
    current_user_id = current_user.id

    users = db.session.execute(
        sa.select(models.User)
        .options(joinedload(models.User.champion))
        .where(models.User.paid)
    ).scalars().all()

    current_user = db.session.execute(
        sa.select(models.User)
        .options(joinedload(models.User.champion))
        .options(joinedload(models.User.bets).joinedload(models.Bet.match).joinedload(models.Match.team1))
        .options(joinedload(models.User.bets).joinedload(models.Bet.match).joinedload(models.Match.team2))
        .filter_by(id=current_user_id)
    ).unique().scalar_one()

    scoreboards = {challenge: challenge.calculate_scoreboard(users) for challenge in models.Challenge}

    teams = db.session.execute(
        sa.select(models.Team).order_by(models.Team.name)
    ).scalars().all()
    groups = sorted(list({team.group for team in teams}))

    matches = db.session.execute(sa.select(models.Match)).scalars().all()
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
         'avatar': 'https://schosel.net/api/avatars/' + quote(user.name + user.avatar_salt),
         'user_id': user.id,
         'name': user.name,
         'paid': user.paid,
         'reward': sum([scoreboards[challenge][user.id].reward for challenge in models.Challenge]) if user.paid else 0.0}

    if include_champion:
        d['champion'] = apify_team(user.champion) if user.champion is not None else None
        d['champion_correct'] = user.champion_correct

    if include_public_bets:
        d['public_bets'] = apify_matches_with_bets(user.visible_bets)

    if include_private_bets:
        d['private_bets'] = apify_matches_with_bets(user.bets)
        d['first_name'] = user.first_name
        d['last_name'] = user.last_name
        d['email'] = user.email
        d['superbets_placed'] = len([bet for bet in user.bets if bet.supertip])

    # Ranking only works if the user has paid
    if user.paid and include_scores:

        scores = []
        for challenge in models.Challenge:
            challenge_entry = apify_challenge(challenge)

            scoreboard_entry = scoreboards[challenge][user.id]

            challenge_entry['points'] = scoreboard_entry.points
            challenge_entry['rank'] = scoreboard_entry.rank + 1
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
         'stage': match.stage,
         'api_data': match.api_data
         }

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

