from flask.ext.wtf import Form
from wtforms import StringField, PasswordField, BooleanField, \
    SubmitField, SelectField
from wtforms.validators import Required, Length, Email, Regexp, EqualTo
from wtforms import ValidationError
from ..models import User
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from ..payment.models import Plan

class LoginForm(Form):
    email = StringField('Email', validators=[Required(), Length(1, 64),
                                             Email()])
    password = PasswordField('Password', validators=[Required()])
    remember_me = BooleanField('Keep me logged in')
    submit = SubmitField('Log In')


class RegistrationForm(Form):
    email = StringField('Email (please use your work email)',
                        validators=[Required(), Length(1, 64), Email()])
    first_name = StringField('First name', validators=[Required(), Length(1, 64)])
    last_name = StringField('Last name', validators=[Required(), Length(1, 64)])
    password = PasswordField('Password',
                             validators=[
                                 Required(),
                                 EqualTo('password2', message='Passwords must match.')
                             ])
    password2 = PasswordField('Confirm password', validators=[Required()])
    organization_name = StringField('Group / Organization Name',
                                    validators=[Length(1,100), Required()])
    org_size = SelectField( coerce=int)
    submit = SubmitField('Start your Free 2 month Trial')

    def __init__(self, *args, **kwargs):
        super(RegistrationForm, self).__init__(*args, **kwargs)
        self.org_size.choices = [(plan.id, plan.description) for plan in
                                 Plan.query.filter_by(live=True).order_by(Plan.amount).all()]

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')


class ChangePasswordForm(Form):
    old_password = PasswordField('Old password', validators=[Required()])
    password = PasswordField('New password', validators=[
        Required(), EqualTo('password2', message='Passwords must match')])
    password2 = PasswordField('Confirm new password', validators=[Required()])
    submit = SubmitField('Update Password')


class PasswordResetRequestForm(Form):
    email = StringField('Email',
                        validators=[Required(), Length(1, 64), Email()])
    submit = SubmitField('Reset Password')


class PasswordResetForm(Form):
    email = StringField('Email',
                        validators=[Required(), Length(1, 64), Email()])
    password = PasswordField('New Password', validators=[
        Required(), EqualTo('password2', message='Passwords must match')])
    password2 = PasswordField('Confirm password', validators=[Required()])
    submit = SubmitField('Reset Password')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first() is None:
            raise ValidationError('Unknown email address.')


class ChangeEmailForm(Form):
    email = StringField('New Email',
                        validators=[Required(), Length(1, 64), Email()])
    password = PasswordField('Password', validators=[Required()])
    submit = SubmitField('Update Email Address')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')
