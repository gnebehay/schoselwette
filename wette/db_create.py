#!venv/bin/python3

from flask_app import Base, engine

Base.metadata.create_all(engine)
