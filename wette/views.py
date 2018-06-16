import flask
import flask_mail
import flask_login
import hashlib
import markdown
import os.path

from flask_login import login_required

import flask_app
import forms
import models

from flask_app import app

@app.route('/')
@app.route('/index')
def index():

    if flask_login.current_user.is_authenticated:
        return flask.redirect('static')

    form = forms.LoginForm()
    return flask.render_template('index.html', form=form)

@login_required
@app.route('/main')
def main():

    return flask.redirect('static')


@app.route("/logout")
@login_required
def logout():
    flask_login.logout_user()
    return flask.redirect('index')


@app.route('/login', methods=['GET', 'POST'])
def login():

    form = forms.LoginForm()
    if flask.request.method == 'POST' and form.validate():

        salted_password = bytes(app.config['PASSWORD_SALT'] + form.password.data, 'utf-8')
        password_hash = hashlib.md5(salted_password).hexdigest()

        q = flask_app.db_session.query(models.User).filter(
            models.User.email == form.email.data,
            models.User.password == password_hash)

        user = q.first()

        if user is not None:

            flask_login.login_user(user, remember=form.rememberme.data)

            flask.flash('Logged in successfully.')

            next = flask.request.args.get('next')
            # next_is_valid should check if the user has valid
            # permission to access the `next` url

            # return flask.redirect(next or flask.url_for('about'))
            return flask.redirect(next or 'index')
        else:
            flask.flash('Sorry, wrong email or password.')

    return flask.render_template('index.html', form=form)

# TODO: Move this somewhere else
def send_mail(msg):
    try:
        msg.sender = app.config['MAIN_MAIL']
        flask_app.mail.send(msg)
    except:
        print('Tried to send mail, did not work.')
        print(msg)

def send_mail_template(tpl, recipients, **kwargs):
    rendered_mail = flask.render_template('mail/' + tpl, **kwargs)
    subject = rendered_mail.splitlines()[0]
    body = '\n'.join(rendered_mail.splitlines()[1:])

    msg = flask_mail.Message(subject=subject, body=body, recipients=recipients)

    send_mail(msg)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = forms.RegistrationForm()

    if flask.request.method == 'POST' and form.validate():
        user = models.User()
        form.populate_obj(user)

        # Set paid explicitly to False
        user.paid = False

        salted_password = bytes(app.config['PASSWORD_SALT'] + user.password, 'utf-8')
        password_hash = hashlib.md5(salted_password).hexdigest()

        # Create password hash
        user.password = password_hash
        flask_app.db_session.add(user)

        user.create_missing_bets()

        send_mail_template('welcome.eml', recipients=[user.email], user=user)

        send_mail(flask_mail.Message('Neuer Schoselwetter',
                                     body=str(user),
                                     recipients=[app.config['ADMIN_MAIL']]))

        return flask.render_template('register_success.html')

    return flask.render_template('register.html', form=form)

@app.route('/match/<int:match_id>', methods=['GET', 'POST'])
@login_required
def match(match_id):

    match = flask_app.db_session.query(models.Match).filter(models.Match.id == match_id).one()

    form = forms.MatchForm(obj=match)

    if flask.request.method == 'POST' and form.validate():
        form.populate_obj(match)

        # TODO: Re-compute odds of match
        match.compute_odds()

        # TODO: Re-compute points of bets and users
        for bet in match.bets:
            bet.compute_points()
            bet.user.compute_points()

    return flask.render_template('match.html', match=match, form=form)

@app.route('/about')
def about():

    with open(os.path.join(app.static_folder, 'rules.markdown'), 'r', encoding='utf-8') as myfile:
        content = myfile.read()

    content = flask.Markup(markdown.markdown(content))

    return flask.render_template('about.html',content=content)

@app.route('/forgotten')
def forgotten():

    form = forms.ForgottenForm()

    return flask.render_template('forgotten.html', form=form)

@app.route('/admin')
@login_required
def admin():

    if not flask_login.current_user.admin:
        flask.abort(403)

    users = flask_app.db_session.query(models.User).all()
    matches = flask_app.db_session.query(models.Match).order_by(models.Match.date.asc()).all()

    return flask.render_template('admin.html', users=users, matches=matches)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():

    current_user = flask_login.current_user

    form = forms.UserForm(obj=current_user)

    if flask.request.method == 'POST' and form.validate():
        form.populate_obj(current_user)

        flask.flash('Your profile has been updated')
        return flask.redirect('main')

    return flask.render_template('edit_profile.html', form=form)

@app.route('/confirm_payment/<int:user_id>')
@login_required
def confirm_payment(user_id):

    if not flask_login.current_user.admin:
        flask.abort(403)

    user = flask_app.db_session.query(models.User).filter(models.User.id == user_id).one()

    user.paid = True

    send_mail_template('payment_confirmed.eml', recipients=[user.email], user=user)

    return flask.redirect('admin')

@app.route('/make_admin/<int:user_id>')
@login_required
def make_admin(user_id):

    if not flask_login.current_user.admin:
        flask.abort(403)

    user = flask_app.db_session.query(models.User).filter(models.User.id == user_id).one()

    user.admin = True

    return flask.redirect('admin')

@app.route('/make_champion/<int:team_id>')
@login_required
def make_champion(team_id):

    if not flask_login.current_user.admin:
        flask.abort(403)

    teams = flask_app.db_session.query(models.Team)

    for team in teams:
        if team.id == team_id:
            team.champion = True
        else:
            team.champion = False

    return flask.redirect('scoreboard')
