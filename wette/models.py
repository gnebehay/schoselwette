import collections
import datetime
import enum

import sqlalchemy as sa
import sqlalchemy_utils as sa_utils

import flask_app

class Stage(enum.Enum):
    GROUP_STAGE = 'Group stage'
    ROUND_OF_16 = 'Round of 16'
    QUARTER_FINAL = 'Quarter-finals'
    SEMI_FINALS = 'Semi-finals'
    FINAL = 'Final'

class Outcome(enum.Enum):
    TEAM1_WIN = '1'
    DRAW = 'X'
    TEAM2_WIN = '2'

def _get_values(enum_type):
    return [e.value for e in enum_type]

class Bet(flask_app.Base):

    __tablename__ = 'bets'

    id = sa.Column(sa.Integer, primary_key=True)
    user_id = sa.Column(sa.Integer, sa.ForeignKey('users.id'))
    match_id = sa.Column(sa.Integer, sa.ForeignKey('matches.id'))
    outcome = sa.Column(sa.Enum(Outcome, values_callable=_get_values))
    supertip = sa.Column(sa.Boolean, default=False, nullable=False)

    match = sa.orm.relationship('Match', backref='bets')
    user = sa.orm.relationship('User', backref='bets')

    __table_args__ = (sa.UniqueConstraint('user_id', 'match_id'),)


    @property
    def valid(self):
        return self.outcome is not None

    @property
    def points(self):

        # Make sure that outcome is not None
        if not self.valid:
            return 0

        # Make sure that the bet is correct
        if self.outcome != self.match.outcome:
            return 0

        points = self.match.odds[self.outcome]

        if self.supertip:
            points = points * 2

        return points


    def __repr__(self):
        return ('<Bet: id={}, user={}, team1={}, team2={}, stage={}, supertip={}, '
                'outcome={}>').format(
            self.id, self.user.name, self.match.team1.name, self.match.team2.name,
            self.match.stage, self.supertip, self.outcome)

    def apify(self, match=False, user=False):

        d = {}

        d['outcome'] = self.outcome.value if self.outcome is not None else None
        d['supertip'] = self.supertip
        d['points'] = self.points

        if match:
            d['match'] = self.match.apify()

        if user:
            d['user'] = self.user.apify()

        return d


class Match(flask_app.Base):

    __tablename__ = 'matches'

    id = sa.Column(sa.Integer, primary_key=True)
    team1_id = sa.Column(sa.Integer, sa.ForeignKey('teams.id'), nullable=False)
    team2_id = sa.Column(sa.Integer, sa.ForeignKey('teams.id'), nullable=False)
    date = sa.Column(sa.DateTime, nullable=False)
    stage = sa.Column(sa.Enum(Stage, values_callable=_get_values))
    # TODO: non-negative constraint
    goals_team1 = sa.Column(sa.Integer)
    goals_team2 = sa.Column(sa.Integer)

    team1 = sa.orm.relationship('Team', foreign_keys=[team1_id])
    team2 = sa.orm.relationship('Team', foreign_keys=[team2_id])

    __table_args__ = (sa.UniqueConstraint('team1_id', 'team2_id', 'stage'),)

    @property
    def editable(self):
        return self.date > datetime.datetime.now()

    @property
    def outcome(self):
        if self.goals_team1 is None or self.goals_team2 is None:
            return None
        if self.goals_team1 > self.goals_team2:
            return Outcome.TEAM1_WIN
        if self.goals_team1 < self.goals_team2:
            return Outcome.DRAW
        return Outcome.TEAM2_WIN


    # Returns a dictionary from outcome -> odd
    @property
    def odds(self):

        num_players = flask_app.db_session.query(User).filter(User.paid).count()

        # Retrieve all valid outcomes for this match
        valid_outcomes = [bet.outcome for bet in self.bets if bet.valid]

        # Count individual outcomes
        counter = collections.Counter(valid_outcomes)

        # Here we reuse the counter dict for storing the odds
        for o in counter.keys():
            counter[o] = num_players / counter[o] # num_players is always greater than counter

        return counter

    # TODO: Candidate for removal
    @property
    def color(self):

        # Maximal odds, e.g. 14
        num_players = flask_app.db_session.query(User).filter(User.paid).count()

        if num_players == 0:
            return {outcome: 50 for outcome in ['1', 'X', '2']}

        # Retrieve all valid outcomes for this match
        valid_outcomes = [bet.outcome for bet in self.bets if bet.valid]

        color = {}
        for outcome in ['1', 'X', '2']:

            # Range 10-50
            color[outcome] = 10 + int(round(40 * valid_outcomes.count(outcome) / num_players, -1))

        return color

    # Sorts bets
    # 
    @property
    def bets_sorted(self):
        return sorted(self.bets,
                      key=lambda x: (x.points, x.outcome) if x.outcome is not None
                                     else ('1', x.supertip),
                      reverse=True)

    # TODO: Revisit this after jsonification
    def __repr__(self):
        return '<Match: id={}, team1={}, team2={}, date={}, stage={}, goals_team1={}, goals_team2={}>'.format(
            self.id, self.team1.name, self.team2.name, self.date, self.stage, self.goals_team1, self.goals_team2)

    def apify(self, bets=False):

        d = {}
        d['match_id'] = self.id
        d['date'] = self.date.isoformat() + 'Z'

        # TODO: Implement this
        d['status'] = 'over'

        d['outcome'] = self.outcome.value if self.outcome is not None else None
        d['team1_name'] = self.team1.name
        d['team1_iso'] = self.team1.short_name
        d['team1_goals'] = self.goals_team1
        d['team2_name'] = self.team2.name
        d['team2_iso'] = self.team2.short_name
        d['team2_goals'] = self.goals_team2
        d['stage'] = self.stage.value

        odds = {}
        odds[Outcome.TEAM1_WIN.value] = self.odds[Outcome.TEAM1_WIN]
        odds[Outcome.TEAM2_WIN.value] = self.odds[Outcome.TEAM2_WIN]
        odds[Outcome.DRAW.value] = self.odds[Outcome.DRAW]

        d['odds'] = odds

        if bets:
            d['bets'] = [bet.apify(user=True) for bet in self.bets]

        return d

# TODO: Delete
class Message(flask_app.Base):

    __tablename__ = 'chat'

    id = sa.Column(sa.Integer, primary_key=True)
    body = sa.Column(sa.String(2048), nullable=False)
    date = sa.Column(sa.DateTime, nullable=False)
    user_id = sa.Column(sa.Integer, sa.ForeignKey('users.id'))

    user = sa.orm.relationship('User')

class Team(flask_app.Base):

    __tablename__ = 'teams'

    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String(128), nullable=False, unique=True)
    short_name = sa.Column(sa.String(16), nullable=False, unique=True)
    group = sa.Column(sa.String(1), nullable=False)
    champion = sa.Column(sa.Boolean, default=False, nullable=False)

    @property
    def odds(self):

        # Get number of users that placed a bet
        num_total_bets = flask_app.db_session.query(User).filter(User.champion_id is not None).count()

        # Number of users that betted on this particular team
        num_bets_team = len(self.users)

        # Prevent division by 0
        if num_bets_team == 0:
            return 0

        return num_total_bets / num_bets_team


    def __repr__(self):
        return '<Team: id={}, name={}, short_name={}, group={}, champion={}>'.format(
            self.id, self.name, self.short_name, self.group, self.champion)

class User(flask_app.Base):

    __tablename__ = 'users'

    id = sa.Column(sa.Integer, primary_key=True)
    email = sa.Column(sa_utils.EmailType, nullable=False, unique=True, info={'label': 'Email'})
    first_name = sa.Column(sa.String(64), nullable=False, info={'label': 'First Name'})
    last_name = sa.Column(sa.String(64), nullable=False, info={'label': 'Last Name'})
    password = sa.Column(sa.String(64), nullable=False)
    paid = sa.Column(sa.Boolean, nullable=False, default=False)
    admin = sa.Column(sa.Boolean, nullable=False, default=False)
    champion_id = sa.Column(sa.Integer, sa.ForeignKey('teams.id'), nullable=True)
    # TODO: Re-add this
    #passwort_reset_token = sa.Column(sa.String(64), nullable=True)
    #passwort_reset_token_validity = sa.Column(sa.String(64), nullable=True)

    champion = sa.orm.relationship('Team', backref='users')

    # TODO: Make this configurable
    MAX_SUPERTIPS = 4

    @property
    def points(self):

        points = sum([bet.points for bet in self.bets])

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

        all_matches = flask_app.db_session.query(Match)

        matches_of_existing_bets = [bet.match for bet in self.bets]

        matches_without_bets = [match for match in all_matches
                                if match not in matches_of_existing_bets]

        for match in matches_without_bets:
            bet = Bet()
            bet.user = self
            bet.match = match

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

    # All valid bets that are no longer editable, sorted by match date
    @property
    def visible_bets(self):
        visible_bets = [bet for bet in self.bets if bet.valid and not bet.match.editable]
        return sorted(visible_bets, key=lambda bet: bet.match.date)

    def get_id(self):
        return str(self.id)
    # END

    def __repr__(self):
        return '<User: id={}, email={}, first_name={}, last_name={}, paid={}, champion_id={}>'.format(
            self.id, self.email, self.first_name, self.last_name, self.paid, self.champion_id)

    # TODO: Why is this a property of user?
    @property
    def champion_editable(self):
        first_match = flask_app.db_session.query(Match).order_by('date').first()
        return first_match.date > datetime.datetime.now()

    # TODO: Why is this a property of user?
    @property
    def final_started(self):
        final_match = flask_app.db_session.query(Match).filter(Match.stage == Stage.FINAL).one_or_none()

        if final_match is None:
            return False
        return final_match.date < datetime.datetime.now()

    def apify(self, bets=False):

        d = {}
        d['user_id'] = self.id
        d['name'] = self.name
        d['logged_in'] = False # TODO: Not implemented yet
        d['points'] = self.points

        if self.final_started:
            d['champion_id'] = self.champion_id
            d['champion_correct'] = self.champion_correct

        d['visible_supertips'] = self.supertips

        if bets:
            d['bets'] = [bet.apify(match=True) for bet in self.visible_bets]

        return d
