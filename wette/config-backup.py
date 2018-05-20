import os
basedir = os.path.abspath(os.path.dirname(__file__))

EVENT_NAME = 'Schoselwette xxx 20yy'

# Disables recaptcha for local test use
TESTING = True

# Enables CORS
ALLOWED_ORIGINS='http://localhost:8080'

# SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app.db')
SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:root@localhost:3306/schosel2018'
SQLALCHEMY_POOL_RECYCLE = 3600

WTF_CSRF_ENABLED = True
SECRET_KEY = 'my-uber-secret-key'

PASSWORD_SALT = 'my-uber-secred-salt'

# RECAPTCHA_PARAMETERS = {'hl': 'zh', 'render': 'explicit'}
# RECAPTCHA_DATA_ATTRS = {'theme': 'dark'}

RECAPTCHA_PUBLIC_KEY = 'blah'
RECAPTCHA_PRIVATE_KEY = 'blah'

ADMIN_MAIL = 'abc@def.gh'

# This is the sender address of mails
MAIN_MAIL = 'abc@def.gh'

MSG_NOT_PAID = "You have not paid yet. Please contact <a href='mailto:{MAIN_MAIL}'>{MAIN_MAIL}</a> for payment options. If you don't pay until the beginning of the first match, you will be scratched.".format(MAIN_MAIL=MAIN_MAIL)
