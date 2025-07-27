from quart_mail import Mail
from quart_wtf import CSRFProtect

csrf = CSRFProtect()
mail = Mail()