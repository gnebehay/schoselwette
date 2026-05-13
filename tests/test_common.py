import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

from wette import app
from wette import common


class CommonHelpersTest(unittest.TestCase):
    def test_validate_success_returns_none(self):
        schema = {"type": "object", "properties": {"x": {"type": "integer"}}}
        with app.app_context():
            self.assertIsNone(common.validate({"x": 1}, schema))

    def test_validate_failure_returns_json_error_tuple(self):
        schema = {
            "type": "object",
            "properties": {"x": {"type": "integer"}},
            "required": ["x"],
        }
        with app.app_context():
            response, status = common.validate({}, schema)
            self.assertEqual(status, 400)
            self.assertIsInstance(response.get_json(), dict)
            self.assertIn("errors", response.get_json())
            self.assertTrue(response.get_json()["errors"])

    @patch("wette.common.db.session.execute")
    def test_is_before_tournament_start_returns_true_when_no_match(self, execute_mock):
        execute_mock.return_value.scalar.return_value = None
        self.assertTrue(common.is_before_tournament_start())

    @patch("wette.common.db.session.execute")
    def test_is_before_tournament_start_returns_true_for_future_match(
        self, execute_mock
    ):
        future_date = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
            days=1
        )
        execute_mock.return_value.scalar.return_value = Mock(date=future_date)
        self.assertTrue(common.is_before_tournament_start())

    @patch("wette.common.db.session.execute")
    def test_is_before_tournament_start_returns_false_for_past_match(
        self, execute_mock
    ):
        past_date = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)
        execute_mock.return_value.scalar.return_value = Mock(date=past_date)
        self.assertFalse(common.is_before_tournament_start())


if __name__ == "__main__":
    unittest.main()
