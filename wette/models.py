import collections
import datetime
import enum

import sqlalchemy as sa
import sqlalchemy_utils as sa_utils

import flask_app

from flask_app import db


class Outcome(enum.Enum):

    TEAM1_WIN = '1'
    DRAW = 'X'
    TEAM2_WIN = '2'

class Status(enum.Enum):

    SCHEDULED = 'scheduled'
    LIVE = 'live'
    OVER = 'over'


# TODO: Explain why sqlalchemy needs that
def _get_values(enum_type):
    return [e.value for e in enum_type]


class Bet(db.Model):

    __tablename__ = 'bets'

    id = sa.Column(sa.Integer, primary_key=True)
    user_id = sa.Column(sa.Integer, sa.ForeignKey('users.id'))
    match_id = sa.Column(sa.Integer, sa.ForeignKey('matches.id'))
    outcome = sa.Column(sa.Enum(Outcome, values_callable=_get_values))
    supertip = sa.Column(sa.Boolean, default=False, nullable=False)
    points = sa.Column(sa.Float, default=0.0, nullable=False)

    match = sa.orm.relationship('Match', backref='bets')
    user = sa.orm.relationship('User', backref='bets')

    __table_args__ = (sa.UniqueConstraint('user_id', 'match_id'),)


    @property
    def valid(self):
        return self.outcome is not None

    @property
    def correct(self):
        return self.valid and self.outcome == self.match.outcome

    def compute_points(self):

        # Make sure that outcome is not None
        if not self.valid:
            self.points = 0
            return

        # Make sure that the bet is correct
        if self.outcome != self.match.outcome:
            self.points = 0
            return

        points = self.match.odds(users)[self.outcome]

        if self.supertip:
            points = points * 2

        self.points = points

    def __repr__(self):
        return ('<Bet: id={}, user={}, team1={}, team2={}, stage={}, supertip={}, '
                'outcome={}>').format(
            self.id, self.user.name, self.match.team1.name, self.match.team2.name,
            self.match.stage, self.supertip, self.outcome)

    def apify(self, users, match=False, user=False):

        d = {}

        d['outcome'] = self.outcome.value if self.outcome is not None else None
        d['supertip'] = self.supertip
        d['points'] = self.points(users)

        if match:
            d['match'] = self.match.apify(users)

        if user:
            d['user'] = self.user.apify(users)

        return d


class Match(db.Model):

    __tablename__ = 'matches'

    id = sa.Column(sa.Integer, primary_key=True)
    team1_id = sa.Column(sa.Integer, sa.ForeignKey('teams.id'), nullable=False)
    team2_id = sa.Column(sa.Integer, sa.ForeignKey('teams.id'), nullable=False)
    date = sa.Column(sa.DateTime, nullable=False)
    stage = sa.Column(sa.String(256), nullable=False)
    # TODO: non-negative constraint
    goals_team1 = sa.Column(sa.Integer)
    goals_team2 = sa.Column(sa.Integer)
    over = sa.Column(sa.Boolean, nullable=False, default=False)
    odds_team1 = sa.Column(sa.Float, default=0.0, nullable=False)
    odds_draw = sa.Column(sa.Float, default=0.0, nullable=False)
    odds_team2 = sa.Column(sa.Float, default=0.0, nullable=False)

    team1 = sa.orm.relationship('Team', foreign_keys=[team1_id])
    team2 = sa.orm.relationship('Team', foreign_keys=[team2_id])

    __table_args__ = (sa.UniqueConstraint('team1_id', 'team2_id', 'stage'),)

    @property
    def editable(self):
        return self.status == Status.SCHEDULED

    @property
    def outcome(self):
        if self.goals_team1 is None or self.goals_team2 is None:
            return None
        if self.goals_team1 > self.goals_team2:
            return Outcome.TEAM1_WIN
        if self.goals_team1 < self.goals_team2:
            return Outcome.TEAM2_WIN
        return Outcome.DRAW

    @property
    def odds(self):
        return {
                Outcome.TEAM1_WIN: self.odds_team1,
                Outcome.DRAW: self.odds_draw,
                Outcome.TEAM2_WIN: self.odds_team2,
                }

    # Sets the odds properties
    def compute_odds(self):

        num_players = len(users)#flask_app.db.query(User).filter(User.paid).count()

        # Retrieve all valid outcomes for this match
        valid_outcomes = [bet.outcome for bet in self.bets if bet.valid]

        # Count individual outcomes
        counter = collections.Counter(valid_outcomes)

        # Here we reuse the counter dict for storing the odds
        for o in counter.keys():
            counter[o] = num_players / counter[o]  # num_players is always greater than counter

        self.odds_team1 = counter[Outcome.TEAM1_WIN]
        self.odds_draw = counter[Outcome.DRAW]
        self.odds_team2 = counter[Outcome.TEAM2_WIN]

    # TODO: Candidate for removal
    @property
    def color(self):

        # Maximal odds, e.g. 14
        num_players = flask_app.db.query(User).filter(User.paid).count()

        if num_players == 0:
            return {outcome: 50 for outcome in ['1', 'X', '2']}

        # Retrieve all valid outcomes for this match
        valid_outcomes = [bet.outcome for bet in self.bets if bet.valid]

        color = {}
        for outcome in ['1', 'X', '2']:

            # Range 10-50
            color[outcome] = 10 + int(round(40 * valid_outcomes.count(outcome) / num_players, -1))

        return color

    @property
    def status(self):

        # If the begin time is later than the current time, return SCHEDULED
        if self.date > datetime.datetime.utcnow():
            return Status.SCHEDULED

        # Otherwise, the game has at least started

        # If it is not marked as over, it is live
        if not self.over:
            return Status.LIVE

        # Otherwise it is over
        return Status.OVER

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
        d['status'] = self.status.value

        d['outcome'] = self.outcome.value if self.outcome is not None else None
        d['team1_name'] = self.team1.name
        d['team1_iso'] = self.team1.short_name
        d['team1_goals'] = self.goals_team1
        d['team2_name'] = self.team2.name
        d['team2_iso'] = self.team2.short_name
        d['team2_goals'] = self.goals_team2
        d['stage'] = self.stage

        if not self.editable:

            odds = {}
            odds[Outcome.TEAM1_WIN.value] = self.odds[Outcome.TEAM1_WIN]
            odds[Outcome.TEAM2_WIN.value] = self.odds[Outcome.TEAM2_WIN]
            odds[Outcome.DRAW.value] = self.odds[Outcome.DRAW]

            d['odds'] = odds

            if bets:
                d['bets'] = [bet.apify(user=True) for bet in self.bets if bet.user.paid]

        return d


class Team(db.Model):

    __tablename__ = 'teams'

    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String(128), nullable=False, unique=True)
    short_name = sa.Column(sa.String(16), nullable=False, unique=True)
    group = sa.Column(sa.String(1), nullable=False)
    champion = sa.Column(sa.Boolean, default=False, nullable=False)
    odds = sa.Column(sa.Float, nullable=False)

    def compute_odds(self):

        num_players = flask_app.db.query(User).filter(User.paid).count()

        # Number of users that betted on this particular team
        num_bets_team = len(self.users)

        odds = 0

        # Prevent division by 0
        if num_bets_team > 0:
            odds = num_players / num_bets_team

        self.odds = odds


    def __repr__(self):
        return '<Team: id={}, name={}, short_name={}, group={}, champion={}>'.format(
            self.id, self.name, self.short_name, self.group, self.champion)

    def apify(self):

        d = {}
        d['team_id'] = self.id
        d['name'] = self.name
        d['short_name'] = self.short_name
        d['group'] = self.group
        d['champion'] = self.champion
        d['odds'] = self.odds

        return d


class User(db.Model):

    __tablename__ = 'users'

    id = sa.Column(sa.Integer, primary_key=True)
    # TODO: email should be unique, but can currently not be enforced because
    # the column is too large to create an index on it
    email = sa.Column(sa_utils.EmailType, nullable=False, info={'label': 'Email'})
    first_name = sa.Column(sa.String(64), nullable=False, info={'label': 'First Name'})
    last_name = sa.Column(sa.String(64), nullable=False, info={'label': 'Last Name'})
    password = sa.Column(sa.String(64), nullable=False)
    paid = sa.Column(sa.Boolean, nullable=False, default=False)
    admin = sa.Column(sa.Boolean, nullable=False, default=False)
    champion_id = sa.Column(sa.Integer, sa.ForeignKey('teams.id'), nullable=True)
    points = sa.Column(sa.Float, default=0.0, nullable=False)
    supertips = sa.Column(sa.Integer, default=0, nullable=False)
    # TODO: Re-add this
    #passwort_reset_token = sa.Column(sa.String(64), nullable=True)
    #passwort_reset_token_validity = sa.Column(sa.String(64), nullable=True)
    hustler_points = sa.Column(sa.Float, default=0.0, nullable=False)
    hustler_correct_bets = sa.Column(sa.Integer, default=0, nullable=False)
    gambler_points = sa.Column(sa.Float, default=0.0, nullable=False)
    expert_points = sa.Column(sa.Float, default=0.0, nullable=False)
    expert_team_id = sa.Column(sa.Integer, sa.ForeignKey('teams.id'))
    hattrick_points = sa.Column(sa.Float, default=0.0, nullable=False)
    secret_points = sa.Column(sa.Float, default=0.0, nullable=False)

    expert_team = sa.orm.relationship('Team', foreign_keys=expert_team_id)
    champion = sa.orm.relationship('Team', foreign_keys=champion_id, backref='users')

    # Backreffed relationships:
    # -bets

    # TODO: Make this configurable
    MAX_SUPERTIPS = 8

    def compute_points(self):

        points = sum([bet.points(users) for bet in self.bets])

        if self.champion_correct:
            points += self.champion.odds

        self.points = points

    @property
    def champion_correct(self):

        if self.champion is not None:
            if self.champion.champion:
                return True

        return False

    # Achievements
    def compute_hustler(self):

        points = sum([bet.points(users) for bet in self.bets if bet.supertip])

        correct_bets = sum([1 for bet in self.bets if bet.supertip and bet.correct])

        self.hustler_points = points
        self.hustler_correct_bets = correct_bets

    def compute_gambler(self):

        points = 0
        for bet in self.bets:

            if not bet.correct:
                continue

            if bet.match.odds(users)[bet.outcome] == max(bet.match.odds(users).values()):
                points += 1

        self.gambler_points = points

    def compute_expert(self):

        points_per_team = collections.defaultdict(int)

        for bet in self.bets:

            if not bet.correct:
                continue

            # Count points without superbet
            points = bet.match.odds(users)[bet.outcome]

            points_per_team[bet.match.team1] += points
            points_per_team[bet.match.team2] += points

        # Check if dictionary is empty
        if not points_per_team:
            points = 0
            team = None
        else:
            points = max(points_per_team.values())
            team = max(points_per_team, key=points_per_team.get)

        self.expert_points = points
        self.expert_team = team

    def compute_hattrick(self):

        points = 0

        current_streak = -2

        # TODO: Make sure this is sorted properly
        for bet in self.bets:

            if bet.correct:
                current_streak += 1

                points += max(0, current_streak)

            else:
                current_streak = -2

        self.hattrick_points = points

    def compute_secret(self):

        points = 0
        for bet in self.bets:

            if not bet.valid:
                continue

            if bet.outcome != bet.match.outcome:
                points += 1

        self.secret_points = points

    def create_missing_bets(self):

        all_matches = flask_app.db.query(Match)

        matches_of_existing_bets = [bet.match for bet in self.bets]

        matches_without_bets = [match for match in all_matches
                                if match not in matches_of_existing_bets]

        for match in matches_without_bets:
            bet = Bet()
            bet.user = self
            bet.match = match

    @property
    def compute_supertips(self):
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

        # TODO TODO TODO: Needs to be fixed
        return False
        first_match = flask_app.db.query(Match).order_by('date').first()
        return first_match.date > datetime.datetime.utcnow()

    # TODO: This seems not to be used for anything anyway
    # TODO: Why is this a property of user?
    @property
    def final_started(self):

        # TODO TODO TODO: Needs to be fixed
        return False
        final_match = flask_app.db.query(Match).filter(Match.stage == Stage.FINAL).one_or_none()

        if final_match is None:
            return False
        return final_match.date < datetime.datetime.utcnow()

    def apify(self, bets=False, show_private=False, users=False):

        d = {}
        d['user_id'] = self.id
        d['name'] = self.name
        d['logged_in'] = False  # TODO: Not implemented yet
        d['points'] = self.points
        d['admin'] = self.admin
        d['paid'] = self.paid

        if not self.champion_editable or show_private:
            d['champion'] = self.champion.apify() if not self.champion is None else None
            d['champion_correct'] = self.champion_correct

        d['visible_supertips'] = self.supertips

        if bets:
            d['bets'] = [bet.apify(match=True) for bet in self.visible_bets]

        if users:

            d['rank'] = sorted([user.points for user in users], reverse=True).index(self.points)+1

            hustler = {}
            hustler['score'] = self.hustler_points
            hustler['correct_bets'] = self.hustler_correct_bets
            hustler['rank'] = sorted([user.hustler_points for user in users], reverse=True).index(self.hustler_points)+1

            gambler = {}
            gambler['score'] = self.gambler_points
            gambler['rank'] = sorted([user.gambler_points for user in users], reverse=True).index(self.gambler_points)+1

            expert = {}
            expert['score'] = self.expert_points
            expert['team'] = self.expert_team.apify() if not self.expert_team is None else None
            expert['rank'] = sorted([user.expert_points for user in users], reverse=True).index(self.expert_points)+1

            hattrick = {}
            hattrick['score'] = self.hattrick_points
            hattrick['rank'] = sorted([user.hattrick_points for user in users], reverse=True).index(self.hattrick_points)+1

            secret = {}
            secret['score'] = self.secret_points
            secret['rank'] = sorted([user.secret_points for user in users], reverse=True).index(self.secret_points)+1

            achievements = {}
            achievements['hustler'] = hustler
            achievements['gambler'] = gambler
            achievements['expert'] = expert
            achievements['hattrick'] = hattrick
            achievements['secret'] = secret

            d['achievements'] = achievements

        return d
