import logging
import os

import flask
import flask_cors
import flask_login
import flask_mail
import flask_sqlalchemy

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
merge_env_config('FOOTBALL_API_KEY')
merge_env_config('FOOTBALL_API_LEAGUE')

mail = flask_mail.Mail(app)

db = flask_sqlalchemy.SQLAlchemy(app)

migrate = Migrate(app, db, render_as_batch=True)

# logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

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
    print('CORS support enabled')
    flask_cors.CORS(app, origins=app.config['ALLOWED_ORIGINS'], supports_credentials=True)
