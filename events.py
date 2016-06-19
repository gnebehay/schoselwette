from flask import session
from flask.ext.socketio import emit, join_room, leave_room
from wette import socketio
import datetime

from flask_login import current_user


from models import Message

from wette import db_session

@socketio.on('joined', namespace='/chat')
def joined(message):
    """Sent by clients when they enter a room.
    A status message is broadcast to all people in the room."""
    room = session.get('room')
    join_room(room)
    emit('status', {'msg': current_user.name + ' has entered the chat.'})


@socketio.on('text', namespace='/chat')
def text(message):
    """Sent by a client when the user entered a new message.
    The message is sent to all people in the room."""

    msg = Message()
    msg.user = current_user
    msg.body = message['msg']
    msg.date = datetime.datetime.now()

    db_session.add(msg)
    db_session.commit()

    emit('message', {'msg': msg.date.strftime("%H:%M:%S") + ' ' + msg.user.name + ': ' + msg.body})


@socketio.on('left', namespace='/chat')
def left(message):
    """Sent by clients when they leave a room.
    A status message is broadcast to all people in the room."""
    emit('status', {'msg': current_user.name + ' has left the room.'})
