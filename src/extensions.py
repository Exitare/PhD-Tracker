from flask_mail import Mail
from flask_wtf import CSRFProtect

csrf = CSRFProtect()
mail = Mail()