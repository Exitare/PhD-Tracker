from quart_wtf import QuartForm
from wtforms import StringField, PasswordField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, Length


class EmailForm(QuartForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Current Password", validators=[DataRequired()])


class PasswordForm(QuartForm):
    current_password = PasswordField("Current Password", validators=[
        DataRequired(message="Please enter your current password.")
    ])
    password = PasswordField("New Password", validators=[
        DataRequired(),
        Length(min=6, message="Password must be at least 6 characters.")
    ])
    confirm = PasswordField("Confirm Password", validators=[
        DataRequired(),
        EqualTo('password', message="Passwords must match.")
    ])


class ThemeForm(QuartForm):
    theme = SelectField("Design Theme", choices=[
        ("lavender-dark", "Lavender (Dark)"),
        ("lavender-light", "Lavender (Light)"),
        ("solarized-dark", "Solarized (Dark)"),
        ("solarized-light", "Solarized (Light)")
    ])
