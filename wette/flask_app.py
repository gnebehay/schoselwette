import flask
import flask_login
import flask_mail
import flask_wtf
import sqlalchemy
import wtforms_alchemy

# TODO: Add some more explanation here what all of this is good for

app = flask.Flask(__name__)

# TODO: What is this doing here?
app.debug = True

mail = flask_mail.Mail(app)

# Enable Csrf protection
flask_wtf.csrf.CSRFProtect(app)

# Load the config file
app.config.from_object('config')

# Create login manager
login_manager = flask_login.LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Establish database connection
engine = sqlalchemy.create_engine(
    app.config['SQLALCHEMY_DATABASE_URI'],
    convert_unicode=True,
    pool_recycle=app.config['SQLALCHEMY_POOL_RECYCLE'])

db_session = sqlalchemy.orm.scoped_session(
    sqlalchemy.orm.sessionmaker(autocommit=False, autoflush=False, bind=engine))
Base = sqlalchemy.ext.declarative.declarative_base()
Base.query = db_session.query_property()

# import logging
# logging.basicConfig()
# logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# Cleanup
@app.teardown_appcontext
def shutdown_session(exception=None):
    try:
        db_session.commit()
    except:
        db_session.rollback()
        raise


# This code is needed to make form generation work
BaseModelForm = wtforms_alchemy.model_form_factory(flask_wtf.FlaskForm)

# TODO: What is this good for?
class ModelForm(BaseModelForm):
    @classmethod
    def get_session(self):
        return db_session


from models import User # noqa

@login_manager.user_loader
def load_user(user_id):

    q = db_session.query(User).filter(User.id == user_id)
    return q.one_or_none()

# This import is at the end to avoid circular imports (e.g. app would not be found)
import models # noqa
import views # noqa
import api # noqa
