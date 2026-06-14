import logging
import time
from datetime import datetime, timedelta

import requests
import sqlalchemy as sa
from sqlalchemy.orm import joinedload

from . import app, common, db, metrics, models
from .api import admin

logger = logging.getLogger(__name__)

WC2026_API_BASE_URL = "https://api.wc2026api.com"


@app.cli.command("sync_matches")
def sync_matches():
    try:
        _sync_matches()
    except Exception:
        logger.exception("sync_matches failed")
        raise


def _sync_matches():
    logger.info("Syncing matches")

    fixtures = request_fixtures()

    logger.info("Fetched %d fixtures from API", len(fixtures))

    new_matches_created = False

    for fixture in fixtures:
        match = {
            "team1Name": fixture["home_team"],
            "team1Code": fixture["home_team_code"],
            "team2Name": fixture["away_team"],
            "team2Code": fixture["away_team_code"],
            "group": fixture["group_name"],
            "stage": fixture["round"],
            "dateTime": normalize_datetime(fixture["kickoff_utc"]),
            "fixture_id": fixture["id"],
        }

        if match["team1Name"] is None or match["team2Name"] is None:
            logger.warning(
                f"Warning: skipping fixture {fixture['id']} because team names are missing."
            )
            continue

        new_match_created = admin.process_match(match, fixture)

        new_matches_created = new_matches_created or new_match_created

    logger.info("Syncing matches done")

    if new_matches_created:
        all_users = db.session.execute(sa.select(models.User)).scalars().all()

        for user in all_users:
            common.send_mail_template(
                "new_match_notification.eml", recipients=[user.email], user=user
            )


@app.cli.command("sync_outcomes")
def sync_outcomes():
    try:
        _sync_outcomes()
    except Exception:
        logger.exception("sync_outcomes failed")
        raise


def _sync_outcomes():
    logger.info("Syncing outcomes")

    matches = (
        db.session.execute(
            sa.select(models.Match)
            .options(joinedload(models.Match.team1))
            .options(joinedload(models.Match.team2))
        )
        .scalars()
        .all()
    )

    live_matches = [
        match
        for match in matches
        if match.status == models.Status.LIVE and match.fixture_id is not None
    ]

    logger.info("Processing %d live matches", len(live_matches))

    if not live_matches:
        logger.info("No live matches, stopping.")
        return

    logger.info("Requesting fixtures from WC2026 API.")

    fixtures = request_fixtures(status=["live", "completed"])
    fixtures_by_id = {fixture["id"]: fixture for fixture in fixtures}

    for live_match in live_matches:
        fixture = fixtures_by_id.get(live_match.fixture_id)
        if fixture is None:
            logger.warning(
                f"Warning: fixture {live_match.fixture_id} not found in API response."
            )
            continue

        live_match.api_data = fixture
        live_match.goals_team1 = fixture.get("home_score")
        live_match.goals_team2 = fixture.get("away_score")

        if live_match.goals_team1 is None or live_match.goals_team2 is None:
            continue

        if fixture.get("status") == "completed":
            live_match.over = True

        if live_match.first_goal == models.Outcome.DRAW:
            if live_match.goals_team1 > 0 and live_match.goals_team2 == 0:
                live_match.first_goal = models.Outcome.TEAM1_WIN
            elif live_match.goals_team2 > 0 and live_match.goals_team1 == 0:
                live_match.first_goal = models.Outcome.TEAM2_WIN
            elif live_match.goals_team1 > 0 and live_match.goals_team2 > 0:
                pass
                # TODO In this case we don't know anything and should ask admins for help
                # But watch out that we only send this once

    users = common.query_paying_users()
    for user in users:
        user.compute_points()

    logger.info("Syncing outcomes done")


def normalize_datetime(datetime_string):
    if datetime_string is None:
        return None
    if datetime_string.endswith("Z"):
        return datetime_string[:-1] + "+00:00"
    return datetime_string


def request_fixtures(status=None):
    api_key = app.config.get("WC2026_API_KEY")
    if not api_key:
        raise RuntimeError("WC2026_API_KEY is required to fetch WC2026 fixtures")

    params = {}
    # if status:
    #    params["status"] = status

    # Enforce daily request limit if configured. Counts rolling last 24 hours.
    max_requests = app.config.get("WC2026_API_MAX_REQUESTS_PER_DAY")
    endpoint = f"{WC2026_API_BASE_URL}/matches"
    if max_requests is not None:
        cutoff = datetime.utcnow() - timedelta(days=1)
        try:
            recent_count = (
                db.session.execute(
                    sa.select(sa.func.count())
                    .select_from(metrics.SyncMetric)
                    .where(metrics.SyncMetric.endpoint == endpoint)
                    .where(metrics.SyncMetric.timestamp >= cutoff)
                )
            ).scalar()
        except Exception:
            logger.exception("Failed to count recent sync metrics; allowing request")
            recent_count = 0

        if recent_count is not None and recent_count >= max_requests:
            raise RuntimeError(
                f"WC2026 API daily request limit reached ({max_requests} per 24h)"
            )

    start = time.perf_counter()
    response = None
    try:
        response = requests.get(
            url=f"{WC2026_API_BASE_URL}/matches",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
            },
            params=params,
            timeout=10,
        )
        if response.status_code == 401:
            logger.error(
                "WC2026 API token rejected with 401 Unauthorized. "
                "Please verify WC2026_API_KEY and ensure the token is accepted by the API."
            )
        response.raise_for_status()

        fixtures = response.json()
        if not isinstance(fixtures, list):
            raise RuntimeError(
                "Unexpected response from WC2026 API: expected a list of matches"
            )

        return fixtures
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        try:
            status_code = response.status_code if response is not None else None
            metric = metrics.SyncMetric(
                endpoint=f"{WC2026_API_BASE_URL}/matches",
                method="GET",
                status_code=status_code,
                duration_ms=round(duration_ms, 2),
            )
            db.session.add(metric)
        except Exception:
            logger.exception("Failed to record sync metric")
