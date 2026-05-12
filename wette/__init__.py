import logging
import re
import os
import sys

import flask
import flask_cors
import flask_login
import flask_mail
import flask_sqlalchemy

from logging.handlers import RotatingFileHandler
from sqlalchemy import event
from sqlalchemy.engine import Engine
from flask_migrate import Migrate


def merge_env_config(config_key):
    env_config_value = os.environ.get(config_key)
    if env_config_value is not None:
        app.config[config_key] = env_config_value


logging.basicConfig()

# Create flask app
app = flask.Flask(__name__)

# Load the config file
app.config.from_pyfile('config.py')

merge_env_config('SQLALCHEMY_DATABASE_URI')
merge_env_config('WC2026_API_KEY')

#
# Logging setup
#

# Ensure log directory exists
os.makedirs("logs", exist_ok=True)

# Ensure cache directory exists
os.makedirs("cache/avatars", exist_ok=True)


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
    logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
)
root_logger.addHandler(stdout_handler)

# rotating file handler
file_handler = RotatingFileHandler(
    "logs/app.log",
    maxBytes=10_000_000,
    backupCount=5,
)

file_handler.setFormatter(
    StripAnsiFormatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
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

login_manager = flask_login.LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(models.User, int(user_id))


from . import api  # noqa
from . import admin  # noqa
from . import sync  # noqa

# Enable CORS, if requested
if 'ALLOWED_ORIGINS' in app.config:
    logger.info('CORS support enabled')
    flask_cors.CORS(app, origins=app.config['ALLOWED_ORIGINS'], supports_credentials=True)

logger.info("Application started with arguments %s", sys.argv)