import flask
import flask_mail
import flask_login
import hashlib

from flask_login import login_required

import flask_app
import forms
import models

from flask_app import app


@app.route('/')
@app.route('/index')
def index():

    # TODO: Why is this here?
    if flask_login.current_user.is_authenticated:
        return flask.redirect('main')

    return flask.render_template('index.html')


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

            return flask.redirect(next or flask.url_for('index'))
        else:
            flask.flash('Username/Password combination incorrect')

    return flask.render_template('login.html', form=form)

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

@app.route('/')
@app.route('/main', methods=['GET', 'POST'])
@login_required
def main():

    current_user = flask_login.current_user

    if not current_user.paid:
        flask.flash(flask.Markup(app.config['MSG_NOT_PAID']))

    form = forms.ChampionForm(obj=current_user)

    # TODO: Where to put this?
    all_teams = flask_app.db_session.query(models.Team).order_by('name')
    form.champion_id.choices = [(None, '')] + [(team.id, team.name) for team in all_teams]

    if flask.request.method == 'POST':

        # This is important, otherwise the tip gets lost.
        if current_user.champion_editable:

            # This is just for the champion tip
            if form.validate():

                form.populate_obj(current_user)

        # We only deal with editable bets here so that we do not by accident change old data
        editable_bets = [bet for bet in current_user.bets if bet.match.editable]

        flashTooManySupertips = False

        # Iterate over all editable tips
        for bet in editable_bets:
            # We need to set all supertips and outcomes to None/False,
            # as unechecked boxes and radio fields are not contained in the form

            bet.outcome = None
            bet.supertip = False

            outcomeField = 'outcome-{}'.format(bet.match.id)
            supertipField = 'supertip-{}'.format(bet.match.id)

            if outcomeField in flask.request.form:
                bet.outcome = flask.request.form[outcomeField]

            if supertipField in flask.request.form:
                # No matter what was submitted, it means the box was checked
                if current_user.supertips < models.User.MAX_SUPERTIPS:
                    bet.supertip = True
                else:
                    flashTooManySupertips = True

        if flashTooManySupertips:
            flask.flash('You selected too many super bets.')

    if current_user.champion is None:
        flask.flash('The champion bet can be changed until the first match begins.')

    if current_user.supertips < models.User.MAX_SUPERTIPS:
        flask.flash('Super bets can be used only in the group stage.')


    sorted_bets = sorted(current_user.bets, key=lambda x: x.match.date)

    return flask.render_template('main.html', bets=sorted_bets, form=form)

@app.context_processor
def rankings():

    current_user = flask_login.current_user

    if not current_user.is_authenticated:
        return {}

    users = flask_app.db_session.query(models.User).filter(models.User.paid)

    users_sorted = sorted(users, key=lambda x: x.points, reverse=True)

    if not current_user.paid:
        myrank = 0
    else:
        myrank = users_sorted.index(current_user)+1

    return dict(rankings=users_sorted, myrank=myrank)

@app.route('/scoreboard')
@login_required
def scoreboard():

    return flask.render_template('scoreboard.html')

@app.route('/user/<int:user_id>')
@login_required
def user(user_id):

    user = flask_app.db_session.query(models.User).filter(models.User.id == user_id).one()

    return flask.render_template('user.html', user=user)


@app.route('/match/<int:match_id>', methods=['GET', 'POST'])
@login_required
def match(match_id):

    match = flask_app.db_session.query(models.Match).filter(models.Match.id == match_id).one()

    form = forms.MatchForm(obj=match)

    if flask.request.method == 'POST' and form.validate():
        form.populate_obj(match)

    return flask.render_template('match.html', match=match, form=form)

@app.route('/about')
def about():
    return flask.render_template('about.html', match=match)

@app.route('/forgotten')
def forgotten():

    form = forms.ForgottenForm()

    return flask.render_template('forgotten.html', form=form)

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

    # TODO: Here, there should actually be a db commit, no?

    send_mail_template('payment_confirmed.eml', recipients=[user.email], user=user)

    return flask.render_template('user.html', user=user)

# TODO: delete this
@app.route('/chat')
@login_required
def chat():

    messages = flask_app.db_session.query(models.Message)
    # .filter(models.Message.date > datetime.date.today())

    return flask.render_template('chat.html', messages=messages)

@app.route('/stats')
@login_required
def stats():

    teams = flask_app.db_session.query(models.Team)

    teams = sorted(teams, key=lambda t: t.odds, reverse=True)

    return flask.render_template('stats.html', teams=teams)

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
