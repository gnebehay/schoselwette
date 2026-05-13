import unittest
from unittest.mock import Mock, patch

from wette import app
from wette import sync


class SyncHelpersTest(unittest.TestCase):
    def test_normalize_datetime_handles_z_suffix(self):
        self.assertEqual(
            sync.normalize_datetime("2026-06-01T12:00:00Z"), "2026-06-01T12:00:00+00:00"
        )

    def test_normalize_datetime_returns_none_for_none(self):
        self.assertIsNone(sync.normalize_datetime(None))

    def test_normalize_datetime_leaves_non_z_value_unchanged(self):
        self.assertEqual(
            sync.normalize_datetime("2026-06-01T12:00:00+01:00"),
            "2026-06-01T12:00:00+01:00",
        )

    @patch("wette.sync.requests.get")
    def test_request_fixtures_requires_api_key(self, requests_get):
        with app.app_context():
            app.config.pop("WC2026_API_KEY", None)
            with self.assertRaises(RuntimeError):
                sync.request_fixtures()
            requests_get.assert_not_called()

    @patch("wette.sync.requests.get")
    def test_request_fixtures_returns_parsed_list(self, requests_get):
        with app.app_context():
            app.config["WC2026_API_KEY"] = "dummy"
            response = Mock()
            response.raise_for_status = Mock()
            response.json.return_value = [{"id": 1, "home_team": "A"}]
            requests_get.return_value = response

            fixtures = sync.request_fixtures(status="live")

            requests_get.assert_called_once()
            self.assertEqual(fixtures, [{"id": 1, "home_team": "A"}])
            self.assertEqual(
                requests_get.call_args.kwargs["params"], {"status": "live"}
            )

    @patch("wette.sync.requests.get")
    def test_request_fixtures_raises_for_invalid_response(self, requests_get):
        with app.app_context():
            app.config["WC2026_API_KEY"] = "dummy"
            response = Mock()
            response.raise_for_status = Mock()
            response.json.return_value = {"unexpected": "object"}
            requests_get.return_value = response

            with self.assertRaises(RuntimeError):
                sync.request_fixtures()


if __name__ == "__main__":
    unittest.main()
