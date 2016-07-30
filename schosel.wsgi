import sys
sys.path.insert(0, '/home/georg/Dropbox/misc/wette/euro2016')
activate_this = '/home/georg/Dropbox/misc/wette/euro2016/venv/bin/activate_this.py'
with open(activate_this) as file_:
    exec(file_.read(), dict(__file__=activate_this))
from wette import app as application
