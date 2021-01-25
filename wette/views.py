import flask
import flask_login

from flask_login import login_required

import flask_app
import models

from flask_app import app

@app.route('/admin')
def admin():

    # if not flask_login.current_user.admin:
    #     flask.abort(403)

    # matches = flask_app.db.query(models.Match).order_by(models.Match.date.asc()).all()

    users = models.User.query.all()
    matches = models.Match.query.all()

    return flask.render_template('admin.html', users=users, matches=matches)


@app.route('/compute_champion_odds')
@login_required
def compute_champion_odds():

    if not flask_login.current_user.admin:
        flask.abort(403)

    teams = flask_app.db_session.query(models.Team).all()

    num_players = flask_app.db.query(models.User).filter(models.User.paid).count()

    for team in teams:
        team.compute_odds(num_players)

    flask.flash('Champion odds have been recomputed.')

    return flask.redirect('admin')

@app.route('/make_admin/<int:user_id>')
@login_required
def make_admin(user_id):

    if not flask_login.current_user.admin:
        flask.abort(403)

    user = flask_app.db_session.query(models.User).filter(models.User.id == user_id).one()

    user.admin = True

    return flask.redirect('admin')

@app.route('/make_champion/<int:team_id>')
@login_required
def make_champion(team_id):

    if not flask_login.current_user.admin:
        flask.abort(403)

    teams = flask_app.db_session.query(models.Team)

    for team in teams:
        if team.id == team_id:
            team.champion = True
        else:
            team.champion = False

    return flask.redirect('scoreboard')
