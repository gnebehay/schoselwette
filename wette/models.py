import collections
import datetime
import enum

import sqlalchemy as sa
import sqlalchemy_utils as sa_utils

from . import db


PRIZE_DISTRIBUTION = collections.defaultdict(
    lambda: 0.0, {
        0: 0.5,
        1: 0.3,
        2: 0.2})

ScoreboardEntry = collections.namedtuple('ScoreboardEntry', ['points', 'rank', 'reward'])

class Outcome(enum.Enum):
    TEAM1_WIN = '1'
    DRAW = 'X'
    TEAM2_WIN = '2'


class Challenge(enum.Enum):
    SCHOSEL = 1
    LOSER = 2
    UNDERDOG = 3
    BALANCED = 4
    COMEBACK = 5

    # TODO: This function gives currently incorrect results if num_users == 1 or num_users == 2
    # TODO: This function might benefit from receiving the scoreboard_entries
    def compute_final_reward(self, num_users, ranking, preliminary_rewards):

        unique_relevant_ranks = list(set([rank for rank in ranking if rank <= 2]))

        final_reward = collections.defaultdict(lambda: 0.0)

        # This can be now only 0, 1, 2
        for unique_rank in unique_relevant_ranks:

            rank_reward_sum = 0.0
            rank_occurrences = 0
            for rank, reward in zip(ranking, preliminary_rewards):
                if rank == unique_rank:
                    rank_reward_sum += reward
                    rank_occurrences += 1

            reward = rank_reward_sum / rank_occurrences

            final_reward[unique_rank] = num_users * 10 / 5 * reward

        return final_reward

    def calculate_scoreboard(self, users):

        sorted_users = sorted(users, key= lambda user: user.points_for_challenge(self), reverse=True)
        sorted_points = [user.points_for_challenge(self) for user in sorted_users]
        ranking = [sorted_points.index(points) for points in sorted_points]
        preliminary_rewards = [PRIZE_DISTRIBUTION[idx] for idx in range(len(users))]
        final_reward_for_rank = self.compute_final_reward(len(users), ranking, preliminary_rewards)

        return {user.id: ScoreboardEntry(points=points, rank=rank, reward=final_reward_for_rank[rank])
                for user, points, rank in zip(sorted_users, sorted_points, ranking)}



class Status(enum.Enum):
    SCHEDULED = 'scheduled'
    LIVE = 'live'
    OVER = 'over'


# sqlalchemy needs this for enums
def _get_values(enum_type):
    return [e.value for e in enum_type]


class Bet(db.Model):
    __tablename__ = 'bets'

    id = sa.Column(sa.Integer, primary_key=True)
    user_id = sa.Column(sa.Integer, sa.ForeignKey('users.id'))
    match_id = sa.Column(sa.Integer, sa.ForeignKey('matches.id'))
    outcome = sa.Column(sa.Enum(Outcome, values_callable=_get_values))
    # TODO: Rename to superbet
    supertip = sa.Column(sa.Boolean, default=False, nullable=False)

    match = sa.orm.relationship('Match', backref='bets')
    user = sa.orm.relationship('User', backref='bets')

    __table_args__ = (sa.UniqueConstraint('user_id', 'match_id'),)

    @property
    def valid(self):
        return self.outcome is not None

    @property
    def correct(self):
        return self.valid and self.outcome == self.match.outcome

    # TODO: Unit test
    def points(self):

        if not self.valid or self.match.editable:
            return {challenge: 0.0 for challenge in Challenge}

        points = int(1 + self.supertip) * self.match.odds[self.outcome]

        is_highest_odds_without_draw = self.match.odds[self.outcome] == max(
            self.match.odds[Outcome.TEAM1_WIN],
            self.match.odds[Outcome.TEAM2_WIN])

        is_draw = self.outcome == Outcome.DRAW

        return {Challenge.SCHOSEL: self.correct * points,
                Challenge.LOSER: (not self.correct) * points,
                Challenge.UNDERDOG: (self.correct and not is_draw and is_highest_odds_without_draw) * points,
                Challenge.BALANCED: (self.correct and is_draw) * points,
                Challenge.COMEBACK: (self.correct and self.match.first_goal != self.outcome and not is_draw) * points}


class Match(db.Model):
    __tablename__ = 'matches'

    id = sa.Column(sa.Integer, primary_key=True)
    team1_id = sa.Column(sa.Integer, sa.ForeignKey('teams.id'), nullable=False)
    team2_id = sa.Column(sa.Integer, sa.ForeignKey('teams.id'), nullable=False)
    date = sa.Column(sa.DateTime, nullable=False)
    stage = sa.Column(sa.String(256), nullable=False)
    goals_team1 = sa.Column(sa.Integer)
    goals_team2 = sa.Column(sa.Integer)
    first_goal = sa.Column(sa.Enum(Outcome, values_callable=_get_values), nullable=False, default='X')
    over = sa.Column(sa.Boolean, nullable=False, default=False)
    odds_team1 = sa.Column(sa.Float, default=0.0, nullable=False)
    odds_draw = sa.Column(sa.Float, default=0.0, nullable=False)
    odds_team2 = sa.Column(sa.Float, default=0.0, nullable=False)
    fixture_id = sa.Column(sa.Integer, nullable=True)
    api_data = sa.Column(sa.JSON, nullable=True)

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

    # TODO: Unit test
    # Sets the odds properties
    def compute_odds(self, num_players):

        # Retrieve all valid outcomes for this match
        valid_outcomes = [bet.outcome for bet in self.bets if bet.valid]

        # TODO: We should assign a value also to outcomes that noone has better for.

        # Count individual outcomes
        counter = collections.Counter(valid_outcomes)

        # Here we reuse the counter dict for storing the odds
        for o in counter.keys():
            counter[o] = num_players / counter[o]  # num_players is always greater than counter

        if Outcome.TEAM1_WIN not in counter.keys():
            counter[Outcome.TEAM1_WIN] = num_players
        if Outcome.DRAW not in counter.keys():
            counter[Outcome.DRAW] = num_players
        if Outcome.TEAM2_WIN not in counter.keys():
            counter[Outcome.TEAM2_WIN] = num_players

        self.odds_team1 = counter[Outcome.TEAM1_WIN]
        self.odds_draw = counter[Outcome.DRAW]
        self.odds_team2 = counter[Outcome.TEAM2_WIN]

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
    @property
    def bets_sorted(self):
        return sorted(self.bets,
                      key=lambda x: (x.points, x.outcome) if x.outcome is not None
                      else ('1', x.supertip),
                      reverse=True)


class Team(db.Model):
    __tablename__ = 'teams'

    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String(128), nullable=False, unique=True)
    short_name = sa.Column(sa.String(3), nullable=False)
    group = sa.Column(sa.String(1), nullable=False)
    champion = sa.Column(sa.Boolean, default=False, nullable=False)
    odds = sa.Column(sa.Float, nullable=False)

    # Backreffed relationships:
    # -users

    def compute_odds(self, num_players):
        # Number of users that betted on this particular team
        num_bets_team = len(self.users)

        odds = 0

        # Prevent division by 0
        if num_bets_team > 0:
            odds = num_players / num_bets_team

        self.odds = odds


class User(db.Model):
    __tablename__ = 'users'

    id = sa.Column(sa.Integer, primary_key=True)
    email = sa.Column(sa_utils.EmailType, nullable=False)
    email_hash = sa.Column(sa.String(320), nullable=False, unique=True)
    first_name = sa.Column(sa.String(64), nullable=False)
    last_name = sa.Column(sa.String(64), nullable=False)
    avatar_salt = sa.Column(sa.String(64), nullable=False, default='')
    password = sa.Column(sa.String(64), nullable=False)
    paid = sa.Column(sa.Boolean, nullable=False, default=False)
    admin = sa.Column(sa.Boolean, nullable=False, default=False)
    champion_id = sa.Column(sa.Integer, sa.ForeignKey('teams.id'), nullable=True)
    schosel_points = sa.Column(sa.Float, default=0.0, nullable=False)
    loser_points = sa.Column(sa.Float, default=0.0, nullable=False)
    underdog_points = sa.Column(sa.Float, default=0.0, nullable=False)
    balanced_points = sa.Column(sa.Float, default=0.0, nullable=False)
    comeback_points = sa.Column(sa.Float, default=0.0, nullable=False)
    champion = sa.orm.relationship('Team', foreign_keys=champion_id, backref='users')
    reset_token = sa.Column(sa.String(64), nullable=True)

    # Backreffed relationships:
    # -bets

    MAX_SUPERBETS = 8

    __challenge_to_attribute = {
        Challenge.SCHOSEL: 'schosel_points',
        Challenge.LOSER: 'loser_points',
        Challenge.UNDERDOG: 'underdog_points',
        Challenge.BALANCED: 'balanced_points',
        Challenge.COMEBACK: 'comeback_points',
    }

    def compute_points(self):

        # These are all dictionaries
        bets_points = [bet.points() for bet in self.bets]

        if self.champion is not None:
            champion_points = self.champion_correct * self.champion.odds
        else:
            champion_points = 0

        challenge_points = {challenge: sum(bet_points[challenge] for bet_points in bets_points) + champion_points
                            for challenge in Challenge}

        self.schosel_points = challenge_points[Challenge.SCHOSEL]
        self.loser_points = challenge_points[Challenge.LOSER]
        self.underdog_points = challenge_points[Challenge.UNDERDOG]
        self.balanced_points = challenge_points[Challenge.BALANCED]
        self.comeback_points = challenge_points[Challenge.COMEBACK]

    def points_for_challenge(self, challenge):
        return self.__getattribute__(self.__challenge_to_attribute[challenge])

    @property
    def champion_correct(self):

        if self.champion is not None:
            if self.champion.champion:
                return True

        return False

    def create_missing_bets(self):

        all_matches = Match.query.all()

        matches_of_existing_bets = [bet.match for bet in self.bets]

        matches_without_bets = [match for match in all_matches
                                if match not in matches_of_existing_bets]

        for match in matches_without_bets:
            bet = Bet()
            bet.user = self
            bet.match = match

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

    # All valid bets that are no longer editable, sorted by match date
    @property
    def visible_bets(self):

        visible_bets = [bet for bet in self.bets if bet.valid and not bet.match.editable]
        return sorted(visible_bets, key=lambda bet: bet.match.date)
