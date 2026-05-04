import requests
import sqlalchemy as sa

from sqlalchemy.orm import joinedload

from . import app
from . import admin
from . import common
from . import db
from . import models


WC2026_API_BASE_URL = "https://api.wc2026api.com"


@app.cli.command("sync_matches")
def sync_matches():
    print('Syncing matches')

    fixtures = request_fixtures()

    new_matches_created = False

    for fixture in fixtures:
        match = {
            'team1Name': fixture['home_team'],
            'team2Name': fixture['away_team'],
            'stage': fixture['round'],
            'dateTime': normalize_datetime(fixture['kickoff_utc']),
            'fixture_id': fixture['id']}

        if match['team1Name'] is None or match['team2Name'] is None:
            print(f'Warning: skipping fixture {fixture["id"]} because team names are missing.')
            continue

        new_match_created = admin.process_match(match, fixture)

        new_matches_created = new_matches_created or new_match_created

    print('Syncing matches done')

    if new_matches_created:

        all_users = db.session.execute(sa.select(models.User)).scalars().all()

        for user in all_users:
            common.send_mail_template('new_match_notification.eml', recipients=[user.email], user=user)




@app.cli.command("sync_outcomes")
def sync_outcomes():
    print('Syncing outcomes')

    matches = db.session.execute(
        sa.select(models.Match)
        .options(joinedload(models.Match.team1))
        .options(joinedload(models.Match.team2))
    ).scalars().all()

    live_matches = [match for match in matches if match.status == models.Status.LIVE and match.fixture_id is not None]

    if not live_matches:
        print('No live matches, stopping.')
        return

    print('Requesting fixtures from football api.')

    fixtures = request_fixtures()
    fixtures_by_id = {fixture['id']: fixture for fixture in fixtures}

    for live_match in live_matches:
        fixture = fixtures_by_id.get(live_match.fixture_id)
        if fixture is None:
            print(f'Warning: fixture {live_match.fixture_id} not found in API response.')
            continue

        live_match.api_data = fixture
        live_match.goals_team1 = fixture.get('home_score')
        live_match.goals_team2 = fixture.get('away_score')

        if live_match.goals_team1 is None or live_match.goals_team2 is None:
            continue

        if fixture.get('status') == 'completed':
            live_match.over = True

        if live_match.first_goal == models.Outcome.DRAW:
            if live_match.goals_team1 > 0 and live_match.goals_team2 == 0:
                live_match.first_goal = models.Outcome.TEAM1_WIN
            elif live_match.goals_team2 > 0 and live_match.goals_team1 == 0:
                live_match.first_goal = models.Outcome.TEAM2_WIN
            elif live_match.goals_team1 > 0 and live_match.goals_team2 > 0:
                pass
                # TODO In this case we don't know anything and should ask admins for help
                # But watch out that we only send this once

    users = common.query_paying_users()
    for user in users:
        user.compute_points()

    print('Syncing outcomes done')


def normalize_datetime(datetime_string):
    if datetime_string is None:
        return None
    if datetime_string.endswith('Z'):
        return datetime_string[:-1] + '+00:00'
    return datetime_string


def request_fixtures():
    api_key = app.config.get('WC2026_API_KEY')
    if not api_key:
        raise RuntimeError('WC2026_API_KEY is required to fetch WC2026 fixtures')

    response = requests.get(
        url=f"{WC2026_API_BASE_URL}/matches",
        headers={
            'Authorization': f"Bearer {api_key}",
            'Accept': 'application/json'
        },
        timeout=10,
    )
    response.raise_for_status()

    fixtures = response.json()
    if not isinstance(fixtures, list):
        raise RuntimeError('Unexpected response from WC2026 API: expected a list of matches')

    #excluded_round = app.config.get('FOOTBALL_API_EXCLUDED_ROUNDS')
    #if excluded_round:
    #    fixtures = [fixture for fixture in fixtures if excluded_round not in fixture.get('round', '')]

    return fixtures
