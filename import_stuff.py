#!venv/bin/python3

import datetime
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

# Group Phase
with open('./misc/group-phase.txt') as f:

    matches = []

    FMT = '({}) {}/{} {}:{} {} vs {} @ {}'

    MONTHS = {'Jun':6}
    STAGE = 'Group stage'

    for line in f.readlines():
        _,month, day, hour, minute, team1, team2,_ = parse(FMT,line)

        team1 = db_session.query(Team).filter(Team.name == team1).one()
        team2 = db_session.query(Team).filter(Team.name == team2).one()

        dt = datetime.datetime(2016, month=MONTHS[month], day=int(day), hour=int(hour), minute=int(minute))

        match = db_session.query(Match).filter(
            Match.team1 == team1,
            Match.team2 == team2,
            Match.stage == STAGE).one_or_none()

        if match is None:
            match = Match(team1=team1, team2=team2, stage=STAGE, date=dt)
            db_session.add(match)
            print('Insert: ' + str(match))
        else:
            print('Match ' + str(match) + ' already in database.')

db_session.commit()

# Group Phase
with open('./misc/round16.txt') as f:

    matches = []

    FMT = '({}) {}/{} {}:{} {} vs {} @ {}'

    MONTHS = {'Jun':6}
    STAGE = 'Round of 16'

    for line in f.readlines():
        _,month, day, hour, minute, team1, team2,_ = parse(FMT,line)

        team1 = db_session.query(Team).filter(Team.name == team1).one()
        team2 = db_session.query(Team).filter(Team.name == team2).one()

        dt = datetime.datetime(2016, month=MONTHS[month], day=int(day), hour=int(hour), minute=int(minute))

        match = db_session.query(Match).filter(
            Match.team1 == team1,
            Match.team2 == team2,
            Match.stage == STAGE).one_or_none()

        if match is None:
            match = Match(team1=team1, team2=team2, stage=STAGE, date=dt)
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
