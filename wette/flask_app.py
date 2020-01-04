import flask
import flask_cors
import flask_mail
import flask_sqlalchemy
import flask_login
import sqlalchemy
import logging

def send_mail(msg):
    try:
        msg.sender = app.config['MAIN_MAIL']
        mail.send(msg)
    except:
        print('Tried to send mail, did not work.')
        print(msg)

def send_mail_template(tpl, recipients, **kwargs):
    rendered_mail = flask.render_template('mail/' + tpl, **kwargs)
    subject = rendered_mail.splitlines()[0]
    body = '\n'.join(rendered_mail.splitlines()[1:])

    msg = flask_mail.Message(subject=subject, body=body, recipients=recipients)

    send_mail(msg)

logging.basicConfig()

# Create flask app
app = flask.Flask(__name__)

# Load the config file
app.config.from_object('config')

mail = flask_mail.Mail(app)

# Establish database connection
engine = sqlalchemy.create_engine(
    app.config['SQLALCHEMY_DATABASE_URI'],
    convert_unicode=True,
    pool_recycle=app.config['SQLALCHEMY_POOL_RECYCLE'])

db = flask_sqlalchemy.SQLAlchemy(app)

logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

import models # noqa

login_manager = flask_login.LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):

    q = models.User.query.filter_by(id=user_id)
    return q.one_or_none()


import api # noqa

#
## TODO: Add some more explanation here what all of this is good for
#
#
## Enable CORS, if requested
#if 'ALLOWED_ORIGINS' in app.config:
#
#    print('CORS support enabled')
#
#    flask_cors.CORS(app, origins=app.config['ALLOWED_ORIGINS'], supports_credentials=True)
#
#    # logging.getLogger('flask_cors').level = logging.DEBUG
#
## Create login manager
#login_manager = flask_login.LoginManager()
#login_manager.init_app(app)
#login_manager.login_view = 'login'
#
#
#
#
## Cleanup
#@app.teardown_appcontext
#def shutdown_session(exception=None):
#    try:
#        db.session.commit()
#    except:
#        db.session.rollback()
#        raise
#
#    db.session.remove()


# This import is at the end to avoid circular imports (e.g. app would not be found)
