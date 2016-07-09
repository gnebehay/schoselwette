#!venv/bin/python3

import datetime
import os

from parse import *

import wette
from wette import db_session
import models

from models import Team, Match, User

#Load teams
with open('./misc/teams.csv') as f:

    FMT = '{},{},{}'

    for line in f.readlines():
        group, name, short_name = parse(FMT, line)

        team = db_session.query(Team).filter(Team.name == name).one_or_none()

        if team is None:

            team = Team(group=group, name=name, short_name=short_name)

            db_session.add(team)


            print('Insert: ' + str(team))

        else:
            print('Team ' + str(team) + ' already in database.')

db_session.commit()

MONTHS = {'Jun':6, 'Jul': 7}

for stage in os.listdir('matches'):

    print('Parsing stage', stage)

    with open(os.path.join('matches',stage)) as f:

        matches = []

        FMT = '{}/{} {}:{} {} - {}'

        for line in f.readlines():
            month, day, hour, minute, team1, team2 = parse(FMT,line)

            team1 = db_session.query(Team).filter(Team.name == team1).one()
            team2 = db_session.query(Team).filter(Team.name == team2).one()

            dt = datetime.datetime(2016, month=MONTHS[month], day=int(day), hour=int(hour), minute=int(minute))

            match = db_session.query(Match).filter(
                Match.team1 == team1,
                Match.team2 == team2,
                Match.stage == stage).one_or_none()

            if match is None:
                match = Match(team1=team1, team2=team2, stage=stage, date=dt)
                db_session.add(match)
                print('Insert: ' + str(match))
            else:
                print('Match ' + str(match) + ' already in database.')

    db_session.commit()

#Create missing bets
users = db_session.query(User)

for user in users:
    print('Creating missing bets for ' + str(user))
    user.create_missing_bets()

db_session.commit()
