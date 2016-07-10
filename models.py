from collections import Counter
from wette import Base, db_session
from sqlalchemy import Column, Boolean, DateTime, String, Integer, ForeignKey, Enum, UniqueConstraint
from sqlalchemy_utils import EmailType
from sqlalchemy.orm import relationship, backref
import datetime

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    email = Column(EmailType, nullable=False, unique=True, info={'label': 'Email'})
    first_name = Column(String(64), nullable=False, info={'label': 'First Name'})
    last_name = Column(String(64), nullable=False, info={'label': 'Last Name'})
    password = Column(String(64), nullable=False)
    paid = Column(Boolean, nullable=False, default=False)
    admin = Column(Boolean, nullable=False, default=False)
    champion_id = Column(Integer, ForeignKey('teams.id'), nullable=True)

    champion = relationship('Team', backref='users')

    MAX_SUPERTIPS = 4

    @property
    def points(self):

        points = sum([bet.points for bet in self.bets])

        print(self.champion)
        print(self.champion_correct)

        if self.champion_correct:
            points += self.champion.odds

        return points

    @property
    def champion_correct(self):
        if self.champion is not None:
            if self.champion.champion:
                return True

        return False


    def create_missing_bets(self):

        all_matches = db_session.query(Match)

        matches_of_existing_bets = [bet.match for bet in self.bets]

        matches_without_bets = [match for match in all_matches if match not in matches_of_existing_bets]

        for match in matches_without_bets:
            bet = Bet()
            bet.user = self
            bet.match = match

    @property
    def bets_sorted(self):
        return sorted(self.bets, key=lambda x: x.match.date)

    @property
    def supertips(self):
        return len([bet for bet in self.bets if bet.supertip])

    @property
    def name(self):
        return self.first_name + ' ' + self.last_name[:1] + '.'

    # BEGIN This is for flask login
    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)
    # END

    def __repr__(self):
        return '<User: id={}, email={}, first_name={}, last_name={}, paid={}, champion_id={}>'.format(
            self.id, self.email, self.first_name, self.last_name, self.paid, self.champion_id)

    @property
    def champion_editable(self):
        first_match = db_session.query(Match).order_by('date').first()
        return first_match.date > datetime.datetime.now()

    @property
    def final_started(self):
        final_match = db_session.query(Match).filter(Match.stage == 'Final').one_or_none()

        if final_match is None:
            return False
        return final_match.date < datetime.datetime.now()


class Team(Base):
    __tablename__ = 'teams'
    id = Column(Integer, primary_key=True)
    name = Column(String(128), nullable=False, unique=True)
    short_name = Column(String(3), nullable=False, unique=True)
    group = Column(String(1), nullable=False)
    champion = Column(Boolean, default=False, nullable=False)

    @property
    def odds(self):

        #Get number of users that placed a bet
        num_total_bets = db_session.query(User).filter(User.champion_id != None).count()

        #Number of users that betted on this particular team
        num_bets_team = len(self.users)

        #Prevent division by 0
        if num_bets_team == 0:
            return 0

        return num_total_bets / num_bets_team


    def __repr__(self):
        return '<Team: id={}, name={}, short_name={}, group={}, champion={}>'.format(
            self.id, self.name, self.short_name, self.group, self.champion)

Outcome = Enum('1', 'X', '2')
Stage = Enum('Group stage', 'Round of 16', 'Quarter-finals', 'Semi-finals', 'Final')

class Match(Base):
    __tablename__ = 'matches'
    id = Column(Integer, primary_key=True)
    team1_id = Column(Integer, ForeignKey('teams.id'), nullable=False)
    team2_id = Column(Integer, ForeignKey('teams.id'), nullable=False)
    date = Column(DateTime, nullable=False)
    stage = Column(Stage)
    #TODO: non-negative constraint
    goals_team1 = Column(Integer)
    goals_team2 = Column(Integer)

    team1 = relationship('Team', foreign_keys=[team1_id])
    team2 = relationship('Team', foreign_keys=[team2_id])
    __table_args__ = (UniqueConstraint('team1_id', 'team2_id', 'stage'),)

    @property
    def editable(self):
        return self.date > datetime.datetime.now()

    @property
    def outcome(self):
        if self.goals_team1 is None or self.goals_team2 is None:
            return None
        if self.goals_team1 > self.goals_team2:
            return '1'
        if self.goals_team1 < self.goals_team2:
            return '2'
        return 'X'

    # Returns a dictionary from outcome -> odd
    @property
    def odds(self):

        valid_bets = [bet for bet in self.bets if bet.valid]
        valid_outcomes = [bet.outcome for bet in valid_bets]

        n = len(valid_bets)

        counter = Counter(valid_outcomes)

        for o in counter.keys():
            counter[o] = n / counter[o] #n is always greater than counter

        return counter

    @property
    def bets_sorted(self):
        return sorted(self.bets, key=lambda x: (x.points, x.outcome if x.outcome is not None else '1', x.supertip), reverse=True)

    def __repr__(self):
        return '<Match: id={}, team1={}, team2={}, date={}, stage={}, goals_team1={}, goals_team2={}>'.format(
            self.id, self.team1.name, self.team2.name, self.date, self.stage, self.goals_team1, self.goals_team2)


class Bet(Base):
    __tablename__ = 'bets'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    match_id = Column(Integer, ForeignKey('matches.id'))
    outcome = Column(Outcome)
    supertip = Column(Boolean, default=False, nullable=False)

    match = relationship('Match', backref='bets')
    user = relationship('User', backref='bets')

    __table_args__ = (UniqueConstraint('user_id', 'match_id'),)

    @property
    def valid(self):
        return self.outcome is not None and self.user.paid

    @property
    def points(self):

        #Make sure that outcome is not None
        if not self.valid:
            return 0

        #Make sure that the bet is correct
        if self.outcome != self.match.outcome:
            return 0

        points = self.match.odds[self.outcome]

        if self.supertip:
            points = points * 2

        return points


    def __repr__(self):
        return '<Bet: id={}, user={}, team1={}, team2={}, stage={}, supertip={}, outcome={}>'.format(
            self.id, self.user.name, self.match.team1.name, self.match.team2.name, self.match.stage, self.supertip, self.outcome)

class Message(Base):
    __tablename__ = 'chat'

    id = Column(Integer, primary_key=True)
    body = Column(String(2048), nullable=False)
    date = Column(DateTime, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'))

    user = relationship('User')
