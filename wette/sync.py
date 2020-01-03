import flask_app
import requests

import models

# Make this configurable
#url = "https://api-football-v1.p.rapidapi.com/v2/fixtures/league/1"
url = "http://localhost:8000/fixtures.json"

# Make this configurable
headers = {
    'x-rapidapi-host': "api-football-v1.p.rapidapi.com",
    'x-rapidapi-key': "cbc894a751mshf02d976c797a674p16a3ecjsn88f7d42065fe"
    }

response = requests.request("GET", url, headers=headers)

import ipdb; ipdb.set_trace()

# TODO: Extract result and do something meaningfule

print(response.text)

# Loop over fixtures

# Check if home team exists
team_db = db_session.query(Team).filter(Team.name == team_csv.name).one_or_none()

if team_db is None:

    team_db = Team(name=team_csv.name)

    db_session.add(team_db)

    print('Insert: ' + str(team_db))

else:
    print('Team ' + str(team_db) + ' already in database.')

# TODO: Set all other fields that might be relevant

# Do the same for the away team
