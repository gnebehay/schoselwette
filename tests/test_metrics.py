import unittest

from wette.metrics import BetMetric
from wette.models import Outcome


class BetMetricModelTest(unittest.TestCase):
    def test_bet_metric_records_user_match_and_outcome(self):
        metric = BetMetric(user_id=7, match_id=13, outcome=Outcome.DRAW)

        self.assertEqual(metric.__tablename__, "bet_metrics")
        self.assertEqual(metric.user_id, 7)
        self.assertEqual(metric.match_id, 13)
        self.assertEqual(metric.outcome, Outcome.DRAW)


if __name__ == "__main__":
    unittest.main()
