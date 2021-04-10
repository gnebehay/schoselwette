import os

import flask
import flask_cors
import flask_mail
import flask_sqlalchemy
import flask_login
import sqlalchemy
import logging

from flask_migrate import Migrate

logging.basicConfig()

# Create flask app
app = flask.Flask(__name__)

# Load the config file
app.config.from_pyfile('config.py')

mail = flask_mail.Mail(app)

_env_db_uri = os.environ.get("DB_URI")

if _env_db_uri is not None:
    app.config['SQLALCHEMY_DATABASE_URI'] = _env_db_uri

# Establish database connection
engine = sqlalchemy.create_engine(
    app.config['SQLALCHEMY_DATABASE_URI'],
    convert_unicode=True,
    pool_recycle=3600)

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

#
## TODO: Add some more explanation here what all of this is good for


# Enable CORS, if requested
if 'ALLOWED_ORIGINS' in app.config:

   print('CORS support enabled')

   flask_cors.CORS(app, origins=app.config['ALLOWED_ORIGINS'], supports_credentials=True)

   # logging.getLogger('flask_cors').level = logging.DEBUG

