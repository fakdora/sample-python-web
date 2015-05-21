from flask.ext.wtf import Form
from wtforms import StringField, TextAreaField, BooleanField, SelectField,\
    SubmitField, HiddenField, TextField
from wtforms.validators import Required, Length, Email


class ContactForm(Form):
  name = TextField("Your Name",  validators=[Required()])
  email = TextField("Your Email",  validators=[Required(), Length(1, 64), Email()])
  subject = TextField("Subject", validators=[Required()])
  message = TextAreaField("Message",  validators=[Required()])
  submit = SubmitField("Send")


class BrainTreeForm(Form):
  submit = SubmitField("Pay $10")