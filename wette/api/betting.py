import flask
import flask_login
import logging
import sqlalchemy as sa

from flask_login import login_required
from sqlalchemy.orm import joinedload

from .. import app
from .. import db
from .. import common
from .. import models

logger = logging.getLogger(__name__)

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
    bet = db.session.execute(
        sa.select(models.Bet).filter_by(user_id=current_user.id, match_id=match_id)
    ).scalar_one_or_none()

    if bet is None:
        flask.abort(404)

    if not bet.match.editable:
        flask.abort(403)

    posted_bet = flask.request.get_json()

    posted_outcome = posted_bet['outcome']
    if posted_outcome:
        bet.outcome = models.Outcome(posted_outcome)
    # TODO: Rename to superbet
    bet.supertip = posted_bet['superbet']

    # TODO: Rename to superbet
    num_superbets = sum([bet.supertip for bet in current_user.bets])

    # Check if supertips are available
    if num_superbets > models.User.MAX_SUPERBETS:
        # TODO: doesn't abort always cause a rollback?
        db.session.rollback()
        flask.abort(418)

    num_users = db.session.execute(
        sa.select(sa.func.count()).select_from(models.User).where(models.User.paid)
    ).scalar()

    bet.match.compute_odds(num_users)

    logger.info('Bet placed by user %s for match %s.', current_user.id, match_id)

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

    teams = db.session.execute(
        sa.select(models.Team).options(joinedload(models.Team.users))
    ).scalars().unique().all()

    try:
        current_user.champion = next(team for team in teams if team.id == champion_id)
    except StopIteration:
        flask.abort(404)

    users = common.query_paying_users()

    num_players = len(users)

    for team in teams:
        team.compute_odds(num_players)

    logger.info('Champion set by user %s', current_user.id)

    return flask.jsonify(success=True)
