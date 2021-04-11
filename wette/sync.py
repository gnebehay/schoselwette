import requests
import json

from . import app
from . import admin


@app.cli.command("sync_matches")
def sync_matches():

    response = requests.get(
        url="https://api-football-v1.p.rapidapi.com/v2/fixtures/league/403",
        headers={
            'x-rapidapi-host': "api-football-v1.p.rapidapi.com",
            'x-rapidapi-key': app.config['FOOTBALL_API_KEY']
        })

    football_api_response = json.loads(response.text)

    # TODO: Validate the result here?

    fixtures = football_api_response['api']['fixtures']
    fixtures = [fixture for fixture in fixtures if app.config['FOOTBALL_API_EXCLUDED_ROUNDS'] not in fixture['round']]

    for fixture in fixtures:
        match = {
            'team1Name': fixture['homeTeam']['team_name'],
            'team2Name': fixture['awayTeam']['team_name'],
            'stage': fixture['round'],
            'dateTime': fixture['event_date']}
        admin.process_match(match)