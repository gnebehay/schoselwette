import requests
import json

from . import app
from . import admin
from . import common
from . import models

from sqlalchemy.orm import joinedload


@app.cli.command("sync_matches")
def sync_matches():

    print('Syncing matches')

    fixtures = request_fixtures()

    for fixture in fixtures:
        match = {
            'team1Name': fixture['homeTeam']['team_name'],
            'team2Name': fixture['awayTeam']['team_name'],
            'stage': fixture['round'],
            'dateTime': fixture['event_date'],
            'fixture_id': fixture['fixture_id']}

        admin.process_match(match, fixture)
    print('Syncing matches done')


@app.cli.command("sync_outcomes")
def sync_outcomes():

    print('Syncing outcomes')

    matches = models.Match.query \
        .options(joinedload(models.Match.team1)) \
        .options(joinedload(models.Match.team2)) \
        .all()

    live_matches = [match for match in matches if match.status == models.Status.LIVE and match.fixture_id is not None]

    # We only continue if there is a match ongoing so that we do not waste API calls.
    if not live_matches:
        print('No live matches, stopping.')
        return

    print('Requesting fixtures from football api.')

    fixtures = request_fixtures()

    fixtures = {fixture['fixture_id']: fixture for fixture in fixtures}

    for live_match in live_matches:

        fixture = fixtures[live_match.fixture_id]

        live_match.api_data = fixture

        live_match.goals_team1 = fixture['goalsHomeTeam']
        live_match.goals_team2 = fixture['goalsAwayTeam']


        # It can happen that the match has started, but the api does not have any score yet
        if live_match.goals_team1 is None or live_match.goals_team2 is None:
            continue

        if fixture['status'] == 'Match Finished':
            live_match.over = True

        if live_match.first_goal == models.Outcome.DRAW:

            if live_match.goals_team1 > 0 and live_match.goals_team2 == 0:
                live_match.first_goal = models.Outcome.TEAM1_WIN

            if live_match.goals_team2 > 0 and live_match.goals_team1 == 0:
                live_match.first_goal = models.Outcome.TEAM2_WIN

            if live_match.goals_team1 > 0 and live_match.goals_team2 > 0:

                pass

                # TODO In this case we don't know anything and should ask admins for help
                # But watch out that we only send this once

    users = common.query_paying_users()
    for user in users:
        user.compute_points()

    print('Syncing outcomes done')



def request_fixtures():
    response = requests.get(
        url="https://api-football-v1.p.rapidapi.com/v2/fixtures/league/" + app.config['FOOTBALL_API_LEAGUE'],
        headers={
            'x-rapidapi-host': "api-football-v1.p.rapidapi.com",
            'x-rapidapi-key': app.config['FOOTBALL_API_KEY']
        })
    football_api_response = json.loads(response.text)
    # TODO: Validate the result here?
    fixtures = football_api_response['api']['fixtures']
    fixtures = [fixture for fixture in fixtures if app.config['FOOTBALL_API_EXCLUDED_ROUNDS'] not in fixture['round']]
    return fixtures