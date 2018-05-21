import flask_wtf
import wtforms.fields as fld
import wtforms.validators as val

import flask_app
import models


def str_or_none(s):
    if s is None:
        return None
    return str(s)

def int_or_none(v):

    try:
        ret = int(v)
    except:
        # TODO: Check exactly what kind of exception occurs here, we do not want to catch everything
        ret = None

    return ret

class LoginForm(flask_wtf.FlaskForm):

    email = fld.html5.EmailField('Email')
    password = fld.PasswordField('Password')
    rememberme = fld.BooleanField('Remember me')

class RegistrationForm(flask_app.ModelForm):

    class Meta:
        model = models.User
        exclude = ['paid', 'admin']

    password = fld.PasswordField('Password', validators=[
        val.Length(min=3),
        val.EqualTo('confirm', message='The passwords do not match.')])

    confirm = fld.PasswordField('Confirm Password')
    recaptcha = flask_wtf.RecaptchaField()

class BetForm(flask_app.ModelForm):
    class Meta:
        model = models.Bet

    # TODO: How can enum be rendered automatically as a select form?
    # TODO: this seems to be a required field. why?
    outcome = fld.RadioField('Label',
                             choices=[(o.value, o.value) for o in models.Outcome],
                             validators=[val.Optional()],
                             coerce=str_or_none)

    # This stuff is important.
    dummy = fld.HiddenField('arsch', default='foo')

class BetsForm(flask_wtf.FlaskForm):
    bets = fld.FieldList(fld.FormField(BetForm))

class ChampionForm(flask_wtf.FlaskForm):
    champion_id = fld.SelectField('Champion', coerce=int_or_none)

class MatchForm(flask_app.ModelForm):
    class Meta:
        model = models.Match
        # TODO: How to include instead of exclude?
        exclude = ['date', 'stage']

class ForgottenForm(flask_wtf.FlaskForm):

    email = fld.html5.EmailField('Email')

class UserForm(flask_app.ModelForm):
    class Meta:
        model = models.User
        exclude = ['paid', 'password']
