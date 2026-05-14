import unittest
from datetime import datetime
from urllib.parse import quote

from wette.api.views import apify_bet, apify_match, apify_team, apify_user
from wette.models import Challenge, Outcome, ScoreboardEntry, Status


class DummyTeam:
    def __init__(self, id, name, short_name, group, champion, odds):
        self.id = id
        self.name = name
        self.short_name = short_name
        self.group = group
        self.champion = champion
        self.odds = odds


class DummyMatch:
    def __init__(self, **kwargs):
        self.editable = False
        for key, value in kwargs.items():
            setattr(self, key, value)


class DummyBet:
    def __init__(self, outcome, superbet, points, match=None):
        self.outcome = outcome
        self.superbet = superbet
        self._points = points
        self.match = match

    def points(self):
        return self._points


class DummyUser:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class ApiHelpersTest(unittest.TestCase):
    def test_apify_team_returns_basic_team_data(self):
        team = DummyTeam(1, "Germany", "GER", "A", True, 2.5)
        expected = {
            "team_id": 1,
            "name": "Germany",
            "short_name": "GER",
            "group": "A",
            "champion": True,
            "odds": 2.5,
        }
        self.assertEqual(apify_team(team), expected)

    def test_apify_match_returns_correct_fields(self):
        match = DummyMatch(
            id=5,
            date=datetime(2026, 6, 1, 12, 0, 0),
            status=Status.LIVE,
            outcome=Outcome.TEAM1_WIN,
            team1=DummyTeam(2, "Team A", "A", "A", False, 1.0),
            team2=DummyTeam(3, "Team B", "B", "A", False, 1.0),
            goals_team1=2,
            goals_team2=1,
            stage="Group",
            api_data={"source": "test"},
            odds={
                Outcome.TEAM1_WIN: 1.0,
                Outcome.DRAW: 1.0,
                Outcome.TEAM2_WIN: 1.0,
            },
        )

        result = apify_match(match)

        self.assertEqual(result["match_id"], 5)
        self.assertEqual(result["status"], "live")
        self.assertEqual(result["outcome"], "1")
        self.assertEqual(result["team1_name"], "Team A")
        self.assertEqual(result["team2_iso"], "B")
        self.assertEqual(result["api_data"], {"source": "test"})

    def test_apify_bet_builds_points_list(self):
        bet = DummyBet(
            outcome=Outcome.TEAM2_WIN,
            superbet=True,
            points={Challenge.SCHOSEL: 1.0, Challenge.LOSER: 0.0},
        )
        result = apify_bet(bet)
        self.assertEqual(result["outcome"], "2")
        self.assertTrue(result["superbet"])
        self.assertEqual(result["points"][0]["challenge_id"], 1)
        self.assertEqual(result["points"][0]["points"], 1.0)

    def test_apify_user_includes_expected_fields(self):
        match = DummyMatch(
            id=10,
            date=datetime(2026, 6, 1, 12, 0, 0),
            status=Status.OVER,
            editable=False,
            outcome=Outcome.TEAM1_WIN,
            team1=DummyTeam(4, "Team A", "A", "A", False, 1.0),
            team2=DummyTeam(5, "Team B", "B", "A", False, 1.0),
            goals_team1=1,
            goals_team2=0,
            stage="Group",
            api_data={},
            odds={
                Outcome.TEAM1_WIN: 1.0,
                Outcome.DRAW: 1.0,
                Outcome.TEAM2_WIN: 1.0,
            },
        )
        bet = DummyBet(
            outcome=Outcome.TEAM1_WIN,
            superbet=False,
            points={Challenge.SCHOSEL: 2.0, Challenge.LOSER: 0.0},
            match=match,
        )
        user = DummyUser(
            admin=False,
            avatar_salt="salt",
            id=1,
            first_name="Alice",
            last_name="Smith",
            paid=True,
            champion=DummyTeam(4, "Team A", "A", "A", True, 2.0),
            champion_correct=True,
            visible_bets=[bet],
            bets=[bet],
            email="alice@example.com",
            name="Alice S",
        )
        scoreboards = {
            challenge: {1: ScoreboardEntry(points=2.0, rank=0, reward=1.0)}
            for challenge in Challenge
        }

        result = apify_user(
            user,
            scoreboards,
            include_public_bets=True,
            include_private_bets=True,
            include_champion=True,
            include_scores=True,
        )

        self.assertEqual(result["user_id"], 1)
        self.assertEqual(result["name"], "Alice S")
        self.assertIn(quote("Alice S" + "salt"), result["avatar"])
        self.assertTrue(result["paid"])
        self.assertEqual(result["champion"]["name"], "Team A")
        self.assertEqual(result["superbets_placed"], 0)
        self.assertIn("private_bets", result)
        self.assertIn("public_bets", result)
        self.assertEqual(result["reward"], 2.0)


if __name__ == "__main__":
    unittest.main()
