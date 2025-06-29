from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, Length

class EmailForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])

class PasswordForm(FlaskForm):
    password = PasswordField("New Password", validators=[
        DataRequired(),
        Length(min=6, message="Password must be at least 6 characters.")
    ])
    confirm = PasswordField("Confirm Password", validators=[
        DataRequired(),
        EqualTo('password', message="Passwords must match.")
    ])

class ThemeForm(FlaskForm):
    theme = SelectField("Design Theme", choices=[
        ("lavender", "Default (Lavender)"),
        ("dark", "Dark"),
        ("light", "Light"),
        ("solarized", "Solarized")
    ])