import sys
sys.path.insert(0, '/home/worlds2018/wette')
activate_this = '/home/worlds2018/venv/bin/activate_this.py'
with open(activate_this) as file_:
    exec(file_.read(), dict(__file__=activate_this))
from flask_app import app as application
