from flask.ext.wtf import Form
from wtforms import StringField, TextAreaField, BooleanField, SelectField,\
    SubmitField, HiddenField
from wtforms.validators import Required, Length, Email, Regexp
from wtforms import ValidationError
from ..models import Role, User
from sqlalchemy import or_, and_

class NameForm(Form):
    first_name = StringField('First Name', validators=[Required()])
    last_name = StringField('Last Name', validators=[Required()])
    submit = SubmitField('Submit')


class EditProfileForm(Form):
    first_name = StringField('First name', validators=[Length(0, 64)])
    last_name = StringField('Last name', validators=[Length(0, 64)])
    position = StringField('Position', validators=[Length(0,64)])
    department = StringField('Department', validators=[Length(0,64)])
    location = StringField('Location', validators=[Length(0, 64)])
    about_me = TextAreaField('About me')
    submit = SubmitField('Submit')


class RecognitionForm(Form):
    nominee_name = StringField('Nominee Name',
                               validators=[Required()])
    description = TextAreaField("Write Description",
                                validators=[Required()])
    organization_id = HiddenField('Organization Id')
    submit = SubmitField('Submit')


# This is used by super admin
class EditProfileSuperAdminForm(Form):
    email = StringField('Email', validators=[Required(), Length(1, 64),
                                             Email()])
    confirmed = BooleanField('Confirmed')
    position = StringField('Position', validators=[Length(0, 64)])
    department = StringField('Department', validators=[Length(0, 64)])
    role = SelectField('Role', coerce=int)
    first_name = StringField('First name', validators=[Length(0, 64)])
    last_name = StringField('Last name', validators=[Length(0, 64)])
    location = StringField('Location', validators=[Length(0, 64)])
    about_me = TextAreaField('About me')
    submit = SubmitField('Submit')

    def __init__(self, user, *args, **kwargs):
        super(EditProfileSuperAdminForm, self).__init__(*args, **kwargs)
        self.role.choices = [(role.id, role.name)
                             for role in Role.query.order_by(Role.name).all()]
        self.user = user

    def validate_email(self, field):
        if field.data != self.user.email and \
                User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')


class EditProfileOrgAdminForm(Form):
    email = StringField('Email', validators=[Required(), Length(1, 64),
                                             Email()])
    position = StringField('Position', validators=[Length(0, 64)])
    department = StringField('Department', validators=[Length(0, 64)])
    role = SelectField('Role', coerce=int)
    first_name = StringField('First name', validators=[Length(0, 64)])
    last_name = StringField('Last name', validators=[Length(0, 64)])
    location = StringField('Location', validators=[Length(0, 64)])
    about_me = TextAreaField('About me')
    submit = SubmitField('Submit')

    def __init__(self, user, *args, **kwargs):
        super(EditProfileOrgAdminForm, self).__init__(*args, **kwargs)
        roles = Role.query.filter(or_(Role.name=='User', Role.name=='Organization Admin'))
        self.role.choices = [(role.id, role.name) for role in roles ]
        self.user = user

    def validate_email(self, field):
        if field.data != self.user.email and \
                User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')