from collections import namedtuple
from werkzeug.datastructures import MultiDict
from flask import abort, flash, render_template, request, redirect, jsonify, url_for, session, Markup
from flask_mail import Message
from flask_login import login_user
from flask_login import logout_user
from flask_login import current_user
from flask_login import login_required
from wette import app, db_session, ModelForm, mail

from models import Bet, User, Match, Outcome, Team

import models

from wtforms.fields import BooleanField, TextField, DecimalField, PasswordField, SelectField, FormField, FieldList, RadioField, HiddenField
from wtforms.fields.html5 import EmailField
from wtforms.validators import Optional, Required, EqualTo, Length

from flask_wtf import Form, RecaptchaField

import hashlib

@app.route('/')
@app.route('/index')
def index():

    if current_user.is_authenticated:
        return redirect('main')

    return render_template('index.html')

class LoginForm(Form):

    email = EmailField('Email')
    password = PasswordField('Password')
    rememberme = BooleanField('Remember me')


class RegistrationForm(ModelForm):
    class Meta:
        model = User
        exclude = ['paid', 'admin']

    password = PasswordField('Password', validators=[Length(min=8), EqualTo('confirm', message='The passwords do not match.')])
    confirm = PasswordField('Confirm Password')
    recaptcha = RecaptchaField()

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect('index')

@app.route('/login', methods=['GET', 'POST'])
def login():

    form = LoginForm()
    if request.method == 'POST' and form.validate():

        q = db_session.query(User).filter(User.email == form.email.data, User.password == hashlib.md5(bytes(app.config['PASSWORD_SALT'] + form.password.data, 'utf-8')).hexdigest())

        user = q.first()

        if user is not None:

            login_user(user, remember=form.rememberme.data)

            flash('Logged in successfully.')

            next = request.args.get('next')
            # next_is_valid should check if the user has valid
            # permission to access the `next` url

            return redirect(next or url_for('index'))
        else:
            flash('Username/Password combination incorrect')

    return render_template('login.html', form=form)

def send_mail(msg):
    try:
        msg.sender = 'euro2016@schosel.net'
        mail.send(msg)
    except:
        print('Tried to send mail, did not work.')
        print(msg)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()

    if request.method == 'POST' and form.validate():
        user = User()
        form.populate_obj(user)

        #Set paid explicitly to False
        user.paid = False

        #Create password hash
        user.password = hashlib.md5(bytes(app.config['PASSWORD_SALT'] + user.password, 'utf-8')).hexdigest()
        db_session.add(user)

        user.create_missing_bets()

        send_mail(Message('Hello',
                  recipients=[user.email]))

        send_mail(Message('Neuer Schoselwetter',
                  body=str(user),
                  recipients=['gnebehay@gmail.com']))

        return render_template('register_success.html')

    return render_template('register.html', form=form)

def str_or_none(s):
    if s is None:
        return None
    return str(s)


class BetForm(ModelForm):
    class Meta:
        model = Bet

    #TODO: How can enum be rendered automatically as a select form?
    #TODO: this seems to be a required field. why?
    outcome = RadioField('Label', choices=[(o,o) for o in Outcome.enums], validators=[Optional()], coerce=str_or_none)

    #This stuff is important.
    dummy = HiddenField('arsch', default='foo')



class BetsForm(Form):
    bets = FieldList(FormField(BetForm))

def int_or_none(v):

    try:
        ret = int(v)
    except:
        #TODO: Check exactly what kind of exception occurs here
        ret = None

    return ret

class ChampionForm(Form):
    champion_id = SelectField('Champion',
        coerce=int_or_none)

@app.route('/')
@app.route('/main', methods=['GET', 'POST'])
@login_required
def main():

    if not current_user.paid:
        flash(Markup("You have not paid yet. Please contact <a href='mailto:euro2016@schosel.net'>euro2016@schosel.net</a> for payment options. If you don't pay until the beginning of the first match, you will be scratched."))

    form = ChampionForm(obj=current_user)
    #TODO: Where to put this?
    form.champion_id.choices=[(None, '')] + [(t.id, t.name) for t in db_session.query(Team).order_by('name')]

    if request.method == 'POST':

        #This is important, otherwise the tip gets lost.
        if current_user.champion_editable:

            #This is just for the champion tip
            if form.validate():

                form.populate_obj(current_user)

        #We only deal with editable bets here so that we do not by accident change old data
        editable_bets = [bet for bet in current_user.bets if bet.match.editable]

        flashTooManySupertips = False

        #Iterate over all editable tips
        for bet in editable_bets:
            # We need to set all supertips and outcomes to None/False,
            # as unechecked boxes and radio fields are not contained in the form

            bet.outcome = None
            bet.supertip = False

            outcomeField = 'outcome-{}'.format(bet.match.id)
            supertipField = 'supertip-{}'.format(bet.match.id)

            if outcomeField in request.form:
                bet.outcome = request.form[outcomeField]

            if supertipField in request.form:
                #No matter what was submitted, it means the box was checked
                if current_user.supertips < User.MAX_SUPERTIPS:
                    bet.supertip = True
                else:
                    flashTooManySupertips = True

        if flashTooManySupertips:
            flash('You selected too many super bets.')

    if current_user.champion == None:
        flash('The champion bet can be changed until the first match begins.')

    if current_user.supertips < User.MAX_SUPERTIPS:
        flash('Super bets can be used only in the group stage.')


    sorted_bets = sorted(current_user.bets, key=lambda x: x.match.date)

    return render_template('main.html', bets=sorted_bets, form=form)

@app.route('/scoreboard')
@login_required
def scoreboard():

    users = db_session.query(User).filter(User.paid)

    users_sorted = sorted(users, key=lambda x: x.points, reverse=True)

    return render_template('scoreboard.html', scoreboard = users_sorted)

@app.route('/user/<int:user_id>')
@login_required
def user(user_id):

    user = db_session.query(User).filter(User.id == user_id).one()

    return render_template('user.html', user=user)

class MatchForm(ModelForm):
    class Meta:
        model = Match
        # TODO: How to include instead of exclude?
        exclude = ['date', 'stage']

@app.route('/match/<int:match_id>', methods=['GET', 'POST'])
@login_required
def match(match_id):

    match = db_session.query(Match).filter(Match.id == match_id).one()

    form = MatchForm(obj=match)

    if request.method == 'POST' and form.validate():
        form.populate_obj(match)

    return render_template('match.html', match=match, form=form)

@app.route('/about')
def about():
    return render_template('about.html', match=match)

class UserForm(ModelForm):
    class Meta:
        model = User
        exclude = ['paid', 'password']

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():

    form = UserForm(obj=current_user)

    if request.method == 'POST' and form.validate():
        form.populate_obj(current_user)

        flash('Your profile has been updated')
        return redirect('main')

    return render_template('edit_profile.html', form=form)

@app.route('/confirm_payment/<int:user_id>')
@login_required
def confirm_payment(user_id):

    if not current_user.admin:
        abort(403)

    user = db_session.query(User).filter(User.id == user_id).one()

    user.paid = True

    body = """Dear {},

your payment has been confirmed.

Happy betting!""".format(user.name)

    send_mail(Message('Payment confirmed',
              body=body,
              recipients=[user.email]))

    return render_template('user.html', user=user)

@app.route('/chat')
@login_required
def chat():

    messages = db_session.query(models.Message)#.filter(models.Message.date > datetime.date.today())

    return render_template('chat.html', messages=messages)

@app.route('/stats')
@login_required
def stats():

    teams = db_session.query(models.Team)

    teams = sorted(teams, key=lambda t: t.odds, reverse=True)

    return render_template('stats.html', teams=teams)

@app.route('/make_champion/<int:team_id>')
@login_required
def make_champion(team_id):

    if not current_user.admin:
        abort(403)

    teams = db_session.query(Team)

    for team in teams:
        if team.id == team_id:
            team.champion = True
        else:
            team.champion = False

    return redirect('scoreboard')
