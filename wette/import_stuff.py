#!/usr/bin/env python3

import datetime
import os

from parse import *

import flask_app
from flask_app import db_session
import models

from models import Team, Match, User

import pandas as pd

# Read Teams
teams_csv = pd.read_csv('../data/Teams.csv')

# Replace missing short names with empty strings
teams_csv.short_name.fillna('', inplace=True)

for team_csv in teams_csv.itertuples():

    team_db = db_session.query(Team).filter(Team.name == team_csv.name).one_or_none()

    if team_db is None:

        team_db = Team(name=team_csv.name)

        db_session.add(team_db)

        print('Insert: ' + str(team_db))

    else:
        print('Team ' + str(team_db) + ' already in database.')

    team_db.group = team_csv.group
    team_db.short_name = team_csv.short_name

db_session.commit()

for stage in models.Stage:

    filename = '../data/' + stage.value

    if not os.path.exists(filename):
        print("'{}' does not exist, skipping".format(filename))
        continue

    matches_csv = pd.read_csv(filename, parse_dates=['date'])

    for match_csv in matches_csv.itertuples():

        print('Looking up {} - {} in {}'.format(match_csv.team1_name, match_csv.team2_name, stage))

        # Don't attempt to put this into the filter condition using a join,
        # we need these objects anyway in order to create the Match object, if it doesn't exist
        team1_db = db_session.query(Team).filter(Team.name == match_csv.team1_name).one()
        team2_db = db_session.query(Team).filter(Team.name == match_csv.team2_name).one()

        match_db = db_session.query(Match).\
            filter(
                Match.team1 == team1_db,
                Match.team2 == team2_db,
                Match.stage == stage
            ).one_or_none()

        # This is necessary because sqlalchemy cannot handle pandas timestamps
        date = match_csv.date.to_pydatetime()

        if match_db is None:
            match_db = Match(team1=team1_db, team2=team2_db, stage=stage, date=date)
            db_session.add(match_db)
            print('Insert: ' + str(match_db))
        else:

            print('Match ' + str(match_db) + ' already in database.')

            # Update date
            match_db.date = date

    db_session.commit()

#Create missing bets
users = db_session.query(User)

for user in users:
    print('Creating missing bets for ' + str(user))
    user.create_missing_bets()

db_session.commit()
