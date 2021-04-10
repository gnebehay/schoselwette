#/bin/bash
FLASK_APP=wette flask db upgrade
gunicorn -b 0.0.0.0:8000 wette:app