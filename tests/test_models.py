import unittest
from datetime import datetime, timedelta

from wette.models import Bet, Challenge, Match, Outcome, Status


class FakeUser:
    def __init__(self, user_id, points):
        self.id = user_id
        self._points = points

    def points_for_challenge(self, challenge):
        return self._points


class BetPointsTest(unittest.TestCase):
    def test_points_when_match_still_editable_returns_zero(self):
        bet = Bet()
        match = Match()
        match.date = datetime.utcnow() + timedelta(days=1)
        match.over = False
        match.odds_team1 = 2.0
        match.odds_draw = 1.5
        match.odds_team2 = 3.0

        bet.match = match
        bet.outcome = Outcome.TEAM1_WIN
        bet.supertip = False

        expected = {
            Challenge.SCHOSEL: 0.0,
            Challenge.LOSER: 0.0,
        }

        self.assertEqual(bet.points(), expected)

    def test_points_for_incorrect_superbet_returns_loser(self):
        match = Match()
        match.date = datetime.utcnow() - timedelta(hours=1)
        match.over = False
        match.goals_team1 = 1
        match.goals_team2 = 2
        match.odds_team1 = 2.0
        match.odds_draw = 1.5
        match.odds_team2 = 3.0
        match.first_goal = Outcome.TEAM2_WIN

        bet = Bet()
        bet.match = match
        bet.outcome = Outcome.TEAM1_WIN
        bet.supertip = True

        expected = {
            Challenge.SCHOSEL: 0.0,
            Challenge.LOSER: 4.0,
        }

        self.assertEqual(bet.points(), expected)


class MatchStatusTest(unittest.TestCase):
    def test_match_status_scheduled(self):
        match = Match()
        match.date = datetime.utcnow() + timedelta(days=1)
        match.over = False

        self.assertEqual(match.status, Status.SCHEDULED)
        self.assertEqual(match.status.value, "scheduled")

    def test_match_status_live(self):
        match = Match()
        match.date = datetime.utcnow() - timedelta(hours=1)
        match.over = False

        self.assertEqual(match.status, Status.LIVE)

    def test_match_status_over(self):
        match = Match()
        match.date = datetime.utcnow() - timedelta(hours=1)
        match.over = True

        self.assertEqual(match.status, Status.OVER)


class MatchOddsTest(unittest.TestCase):
    def test_compute_odds_sets_missing_outcomes_to_num_players(self):
        match = Match()
        bet1 = Bet()
        bet1.outcome = Outcome.TEAM1_WIN
        bet2 = Bet()
        bet2.outcome = Outcome.TEAM1_WIN
        bet3 = Bet()
        bet3.outcome = Outcome.DRAW

        match.bets = [bet1, bet2, bet3]

        match.compute_odds(num_players=10)

        self.assertEqual(match.odds_team1, 10 / 2)
        self.assertEqual(match.odds_draw, 10 / 1)
        self.assertEqual(match.odds_team2, 10)


class ChallengeScoreboardTest(unittest.TestCase):
    def test_calculate_scoreboard_returns_sorted_ranks_and_rewards(self):
        users = [
            FakeUser(user_id=1, points=10),
            FakeUser(user_id=2, points=20),
            FakeUser(user_id=3, points=5),
        ]

        scoreboard = Challenge.SCHOSEL.calculate_scoreboard(users)

        self.assertEqual(scoreboard[2].points, 20)
        self.assertEqual(scoreboard[2].rank, 0)
        self.assertAlmostEqual(scoreboard[2].reward, 15.75)

        self.assertEqual(scoreboard[1].points, 10)
        self.assertEqual(scoreboard[1].rank, 1)
        self.assertAlmostEqual(scoreboard[1].reward, 9.45)

        self.assertEqual(scoreboard[3].points, 5)
        self.assertEqual(scoreboard[3].rank, 2)
        self.assertAlmostEqual(scoreboard[3].reward, 6.3)


class TeamAndUserModelTest(unittest.TestCase):
    def test_team_compute_odds_with_no_bets_sets_zero(self):
        from wette.models import Team

        team = Team()
        team.users = []

        team.compute_odds(num_players=10)

        self.assertEqual(team.odds, 0)

    def test_user_name_returns_first_and_last_initial(self):
        from wette.models import User

        user = User()
        user.first_name = "Alice"
        user.last_name = "Smith"

        self.assertEqual(user.name, "Alice S.")

    def test_user_compute_points_includes_champion(self):
        from wette.models import User, Team

        team = Team()
        team.champion = True
        team.odds = 2.0

        user = User()
        user.bets = []
        user.champion = team
        user.schosel_points = 0.0
        user.loser_points = 0.0

        user.compute_points()

        self.assertEqual(user.schosel_points, 2.0)
        self.assertEqual(user.loser_points, 2.0)


if __name__ == "__main__":
    unittest.main()
