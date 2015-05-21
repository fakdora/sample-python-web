from flask.ext.wtf import Form
from flask.ext.wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, TextAreaField, BooleanField, SelectField,\
    SubmitField, HiddenField, ValidationError
from wtforms.validators import Required, Length, Email, Regexp
from ..models import User


class OrgAdminAddMemberForm(Form):
    email = StringField('Email', validators=[Required(), Length(1, 64),
                                             Email()])
    first_name = StringField('First name', validators=[Length(0, 64)])
    last_name = StringField('Last name', validators=[Length(0, 64)])
    department = SelectField(coerce=int)
    position = StringField('Position name', validators=[Length(0, 64)])
    submit = SubmitField('Register')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')


class OrgAdminAddDeptForm(Form):
    name = StringField('Dept name', validators=[Length(0, 64)])
    submit = SubmitField('Add')


class RecognitionForm(Form):
    nominee = StringField("Nominee's Name", validators=[Required(), Length(1, 64)])
    reason = TextAreaField('Reason', validators=[Required()])
    submit = SubmitField("Make Someone's Day!")


class PrizeAddForm(Form):
    prize = StringField('Examples: $100 gift card, paid day off', validators=[Length(0, 64)])
    submit = SubmitField('Submit')


class AwardAddForm(Form):
    name = StringField('Award name: example) January 2014', validators=[Length(0, 64)])
    current = BooleanField('This will make existing awards into past awards')
    submit = SubmitField('Submit')


class CsvAddForm(Form):
    csv_file = FileField("Employee in CSV" ,validators=[FileRequired(),
                                                        FileAllowed(['csv'], 'CSV Only!')])
    submit = SubmitField('Upload')