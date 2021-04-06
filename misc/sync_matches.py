import os

import requests
import json

schosel_username = os.getenv('USERNAME')
schosel_password = os.getenv('PASSWORD')
football_api_key = os.getenv('APIKEY')

excluded_rounds = 'Qualify'

response = requests.get(
    url="https://api-football-v1.p.rapidapi.com/v2/fixtures/league/403",
    headers={
        'x-rapidapi-host': "api-football-v1.p.rapidapi.com",
        'x-rapidapi-key': football_api_key
    })

football_api_response = json.loads(response.text)
fixtures = football_api_response['api']['fixtures']
fixtures = [fixture for fixture in fixtures if excluded_rounds not in fixture['round']]

with requests.Session() as session:
    session.post('https://schosel.net/api/login', json={'email': schosel_username, 'password': schosel_password})

    for fixture in fixtures:
        json = {
            'team1Name': fixture['homeTeam']['team_name'],
            'team2Name': fixture['awayTeam']['team_name'],
            'stage': fixture['round'],
            'dateTime': fixture['event_date']}
        r = session.post('https://schosel.net/api/admin/match', json=json)

        print(json, r.status_code)
