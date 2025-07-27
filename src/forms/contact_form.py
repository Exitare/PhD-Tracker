# forms.py
from quart_wtf import QuartForm
from wtforms import StringField, TextAreaField
from wtforms.validators import DataRequired, Email, Optional

class ContactForm(QuartForm):
    first_name = StringField("First Name", validators=[DataRequired()])
    last_name = StringField("Last Name", validators=[DataRequired()])
    phone = StringField("Phone", validators=[Optional()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    message = TextAreaField("Message", validators=[DataRequired()])