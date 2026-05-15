from datetime import datetime

from . import db
from .models import Outcome, _get_values


class RequestMetric(db.Model):
    __tablename__ = "request_metrics"

    id = db.Column(db.Integer, primary_key=True)

    timestamp = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    route = db.Column(db.String(255), nullable=False)

    method = db.Column(db.String(10), nullable=False)

    status_code = db.Column(db.Integer, nullable=False)

    duration_ms = db.Column(db.Float, nullable=False)


class BetMetric(db.Model):
    __tablename__ = "bet_metrics"

    id = db.Column(db.Integer, primary_key=True)

    timestamp = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    match_id = db.Column(db.Integer, db.ForeignKey("matches.id"), nullable=False)
    outcome = db.Column(db.Enum(Outcome, values_callable=_get_values), nullable=False)
