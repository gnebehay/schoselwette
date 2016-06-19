from flask import Flask
from flask_wtf import Form
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from flask.ext.socketio import SocketIO
from wtforms_alchemy import model_form_factory

from flask_wtf.csrf import CsrfProtect
from flask_login import LoginManager

from flask_mail import Mail

app = Flask(__name__)
app.debug = True
mail = Mail(app)
socketio = SocketIO()

#Enable Csrf protection
CsrfProtect(app)

#Load the config file
app.config.from_object('config')

#Create login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

#Establish database connection
engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'], convert_unicode=True, pool_recycle=app.config['SQLALCHEMY_POOL_RECYCLE'])
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()

# import logging
# logging.basicConfig()
# logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

#Add zip to jinja templates
@app.template_global(name='zip')
def _zip(*args, **kwargs): #to not overwrite builtin zip in globals
    return zip(*args, **kwargs)

# TODO: What is this good for?
@app.template_filter('as_dict')
def as_dict(obj):
    objdict = {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
    if hasattr(obj, '__jsonattrs__'):
        fncdict = {a: getattr(obj, a)() for a in obj.__jsonattrs__}
        objdict.update(fncdict)

    return objdict



#Cleanup
@app.teardown_appcontext
def shutdown_session(exception=None):
    try:
        db_session.commit()
    except:
        db_session.rollback()
        raise
    finally:
        db_session.remove()

#This code is needed to make form generation work
BaseModelForm = model_form_factory(Form)

class ModelForm(BaseModelForm):
    @classmethod
    def get_session(self):
        return db_session

from models import User

@login_manager.user_loader
def load_user(user_id):

    q = db_session.query(User).filter(User.id == user_id)
    return q.one_or_none()

import views, events

socketio.init_app(app)
