from datetime import datetime

from . import db


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
