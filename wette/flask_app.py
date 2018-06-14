import flask
import flask_cors
import flask_login
import flask_mail
import flask_wtf
import sqlalchemy
import wtforms_alchemy
import logging

# TODO: Add some more explanation here what all of this is good for


app = flask.Flask(__name__)

# Load the config file
app.config.from_object('config')

# TODO: What is this doing here?
app.debug = True

mail = flask_mail.Mail(app)

# Enable Csrf protection
csrf = flask_wtf.csrf.CSRFProtect(app)

# Enable CORS, if requested
if 'ALLOWED_ORIGINS' in app.config:

    print('CORS support enabled')

    flask_cors.CORS(app, origins=app.config['ALLOWED_ORIGINS'], supports_credentials=True)

    # logging.getLogger('flask_cors').level = logging.DEBUG

# Create login manager
login_manager = flask_login.LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):

    q = db_session.query(models.User).filter(models.User.id == user_id)
    return q.one_or_none()


# Establish database connection
engine = sqlalchemy.create_engine(
    app.config['SQLALCHEMY_DATABASE_URI'],
    convert_unicode=True,
    pool_recycle=app.config['SQLALCHEMY_POOL_RECYCLE'])

db_session = sqlalchemy.orm.scoped_session(
    sqlalchemy.orm.sessionmaker(autocommit=False, autoflush=False, bind=engine))
Base = sqlalchemy.ext.declarative.declarative_base()
Base.query = db_session.query_property()


logging.basicConfig()
#logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)


# Cleanup
@app.teardown_appcontext
def shutdown_session(exception=None):
    try:
        db_session.commit()
    except:
        db_session.rollback()
        raise

    db_session.remove()


# This code is needed to make form generation work
BaseModelForm = wtforms_alchemy.model_form_factory(flask_wtf.FlaskForm)

# TODO: What is this good for?
class ModelForm(BaseModelForm):
    @classmethod
    def get_session(self):
        return db_session

# This import is at the end to avoid circular imports (e.g. app would not be found)
import models # noqa
import views # noqa
import api # noqa
