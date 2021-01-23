import os
basedir = os.path.abspath(os.path.dirname(__file__))

EVENT_NAME = 'Schosel &middot; WM 2018'

# TESTING = True

# Enables CORS
ALLOWED_ORIGINS='*'

SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://<user>:<password>@localhost/<database_name>'
SQLALCHEMY_POOL_RECYCLE = 3600
SQLALCHEMY_TRACK_MODIFICATIONS = False

WTF_CSRF_ENABLED = True
SECRET_KEY = '<secret_key>' # @Georg: warum wird SECRET_KEY doppelt definiert? (Zeile 16 & 26)
PASSWORD_SALT = '<password_salt>'

ADMIN_MAIL = 'abc@def.gh'

# This is the sender address of mails
MAIN_MAIL = 'abc@def.gh'

MSG_NOT_PAID = "You have not paid yet. Please contact <a href='mailto:{MAIN_MAIL}'>{MAIN_MAIL}</a> for payment options. If you don't pay until the beginning of the first match, you will be scratched.".format(MAIN_MAIL=MAIN_MAIL)

SECRET_KEY = '<secret_key>' # @Georg: warum wird SECRET_KEY doppelt definiert? (Zeile 16 & 26)

# Flask-User settings
USER_APP_NAME = "Flask-User QuickStart App"      # Shown in and email templates and page footers
USER_ENABLE_EMAIL = False      # Disable email authentication
USER_ENABLE_USERNAME = True    # Enable username authentication
USER_REQUIRE_RETYPE_PASSWORD = False    # Simplify register form
