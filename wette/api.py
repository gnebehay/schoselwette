import flask

import flask_app
import models
import views

from flask_app import app

def apify_match(match):

    m = {}
    m['match_id'] = match.id
    m['date'] = match.date
    m['status'] = 'over'
    m['result'] = match.outcome
    m['team1_name'] = match.team1.name
    m['team1_iso'] = match.team1.short_name
    m['team1_goals'] = match.goals_team1
    m['team2_name'] = match.team2.name
    m['team2_iso'] = match.team2.short_name
    m['team2_goals'] = match.goals_team2

    return m

def apify_user(user):

    u = {}
    u['user_id'] = user.id
    u['name'] = user.name
    u['logged_in'] = False # TODO: Not implemented yet
    u['points'] = user.points
    u['champion_id'] = user.champion_id
    u['champion_correct'] = user.champion_correct
    u['visible_supertips'] = user.supertips

    return u

# TODO: No login for the moment
@app.route('/api/v1/matches')
def matches_api():

    matches = flask_app.db_session.query(models.Match)

    matches_json = flask.jsonify([apify_match(m) for m in matches])

    matches_json.headers['Access-Control-Allow-Origin'] = '*'

    return matches_json

@app.route('/api/v1/users')
def users_api():

    # TODO: Duplicate code
    users = flask_app.db_session.query(models.User).filter(models.User.paid)

    users_sorted = sorted(users, key=lambda x: x.points, reverse=True)

    users_json = flask.jsonify([apify_user(u) for u in users_sorted])

    users_json.headers['Access-Control-Allow-Origin'] = '*'

    return users_json

def status_api():
    """

    {
      "stages": [
	"Group stage",
	"Round of 16",
	"Quarter-finals",
	"Semi-finals",
	"Final"
      ],
      "groups": [
	"A",
	"B",
	"C"
      ],
      "num_users": 42
    }
    """


