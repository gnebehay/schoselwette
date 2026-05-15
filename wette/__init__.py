import logging
import os
import re
import sys
import time
from logging.handlers import RotatingFileHandler

import flask
import flask_cors
import flask_login
import flask_mail
import flask_sqlalchemy
from flask import g, request
from flask_migrate import Migrate
from sqlalchemy import event
from sqlalchemy.engine import Engine


def merge_env_config(config_key):
    env_config_value = os.environ.get(config_key)
    if env_config_value is not None:
        app.config[config_key] = env_config_value


logging.basicConfig()

# Create flask app
app = flask.Flask(__name__)

# Load the config file
app.config.from_pyfile("config.py")

merge_env_config("SQLALCHEMY_DATABASE_URI")
merge_env_config("WC2026_API_KEY")

# Ensure log, cache directories exists
os.makedirs("logs", exist_ok=True)
os.makedirs("cache/avatars", exist_ok=True)

# Logging setup

ANSI_ESCAPE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")


class StripAnsiFormatter(logging.Formatter):
    def format(self, record):
        message = super().format(record)
        return ANSI_ESCAPE.sub("", message)


root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

root_logger.handlers.clear()

# stdout handler
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
)
root_logger.addHandler(stdout_handler)

# rotating file handler
file_handler = RotatingFileHandler(
    "logs/app.log",
    maxBytes=10_000_000,
    backupCount=5,
)

file_handler.setFormatter(
    StripAnsiFormatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
)

root_logger.addHandler(file_handler)

logger = logging.getLogger(__name__)


mail = flask_mail.Mail(app)

db = flask_sqlalchemy.SQLAlchemy(app)

migrate = Migrate(app, db, render_as_batch=True)

# logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


@app.teardown_appcontext
def shutdown_session(exception=None):
    try:
        if exception is None:
            db.session.commit()
        else:
            db.session.rollback()
    finally:
        db.session.remove()


from . import models  # noqa
from . import metrics  # noqa


@app.before_request
def start_timer():
    g.start_time = time.perf_counter()


@app.after_request
def record_metrics(response):

    duration_ms = (time.perf_counter() - g.start_time) * 1000

    route = request.url_rule.rule if request.url_rule else request.path

    metric = metrics.RequestMetric(
        route=route,
        method=request.method,
        status_code=response.status_code,
        duration_ms=round(duration_ms, 2),
    )

    db.session.add(metric)

    return response


login_manager = flask_login.LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(models.User, int(user_id))


from .api import admin  # noqa
from .api import auth  # noqa
from .api import betting  # noqa
from .api import views  # noqa
from . import sync  # noqa


@app.route("/api/health")
def health():
    return {"status": "ok"}, 200


# Enable CORS, if requested
if "ALLOWED_ORIGINS" in app.config:
    logger.info("CORS support enabled")
    flask_cors.CORS(
        app, origins=app.config["ALLOWED_ORIGINS"], supports_credentials=True
    )

logger.info("Application started with arguments %s", sys.argv)
