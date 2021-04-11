import os

import flask
import flask_cors
import flask_mail
import flask_sqlalchemy
import flask_login
import sqlalchemy
import logging

from flask_migrate import Migrate


def merge_env_config(config_key):
    env_config_value  = os.environ.get(config_key)
    if env_config_value is not None:
        app.config[config_key] = env_config_value

logging.basicConfig()

# Create flask app
app = flask.Flask(__name__)

# Load the config file
app.config.from_pyfile('config.py')

merge_env_config('SQLALCHEMY_DATABASE_URI')
merge_env_config('FOOTBALL_API_KEY')

# Establish database connection
engine = sqlalchemy.create_engine(
    app.config['SQLALCHEMY_DATABASE_URI'],
    convert_unicode=True,
    pool_recycle=3600)


mail = flask_mail.Mail(app)

db = flask_sqlalchemy.SQLAlchemy(app)

migrate = Migrate(app, db)

# logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# TODO: flask-sqlalchemy does something similar already
@app.teardown_appcontext
def shutdown_session(exception=None):
    try:
        db.session.commit()
    except:
        db.session.rollback()
        raise

    db.session.remove()

from . import models # noqa

login_manager = flask_login.LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):

    q = models.User.query.filter_by(id=user_id)
    return q.one_or_none()


from . import api # noqa
from . import admin # noqa
from . import sync # noqa


# Enable CORS, if requested
if 'ALLOWED_ORIGINS' in app.config:

   print('CORS support enabled')

   flask_cors.CORS(app, origins=app.config['ALLOWED_ORIGINS'], supports_credentials=True)
