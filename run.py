#!venv/bin/python3

from wette import app, socketio

if __name__ == '__main__':
    socketio.run(app)
