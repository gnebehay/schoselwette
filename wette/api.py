import flask

import flask_app
import models
import views

from flask_app import app


# TODO: No login for the moment
@app.route('/api/v1/matches')
def matches_api():

    matches = flask_app.db_session.query(models.Match)

    matches_json = flask.jsonify([match.apify() for match in matches])

    # TODO: get rid of this
    matches_json.headers['Access-Control-Allow-Origin'] = '*'

    return matches_json

@app.route('/api/v1/matches/<int:match_id>')
def match_api(match_id):

    try:
        match = flask_app.db_session.query(models.Match).filter(models.Match.id == match_id).one()
    except sqlalchemy.orm.exc.NoResultFound:
        return flask.abort(404)

    matches_json = flask.jsonify(match.apify(bets=True))

    # TODO: get rid of this
    matches_json.headers['Access-Control-Allow-Origin'] = '*'

    return matches_json

@app.route('/api/v1/users')
def users_api():

    # TODO: Duplicate code
    users = flask_app.db_session.query(models.User).filter(models.User.paid)

    users_sorted = sorted(users, key=lambda x: x.points, reverse=True)

    users_json = flask.jsonify([user.apify() for user in users_sorted])

    # TODO: get rid of this
    users_json.headers['Access-Control-Allow-Origin'] = '*'

    return users_json

@app.route('/api/v1/users/<int:user_id>')
def user_api(user_id):

    try:
        user = flask_app.db_session.query(models.User).filter(models.User.id == user_id).one()
    except sqlalchemy.orm.exc.NoResultFound:
        return flask.abort(405)

    user_json = flask.jsonify(user.apify(bets=True))

    # TODO: get rid of this
    user_json.headers['Access-Control-Allow-Origin'] = '*'

    return user_json

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


