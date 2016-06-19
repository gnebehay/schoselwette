import os
basedir = os.path.abspath(os.path.dirname(__file__))

SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app.db')
SQLALCHEMY_POOL_RECYCLE = 3600

WTF_CSRF_ENABLED = True
SECRET_KEY = 'my-uber-secret-key'

PASSWORD_SALT = 'my-uber-secred-salt'

# RECAPTCHA_PARAMETERS = {'hl': 'zh', 'render': 'explicit'}
# RECAPTCHA_DATA_ATTRS = {'theme': 'dark'}

RECAPTCHA_PUBLIC_KEY = 'blah'
RECAPTCHA_PRIVATE_KEY = 'blah'
