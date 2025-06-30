from src.db.models import User
from flask import url_for
from flask_mail import Message
from src.extensions import mail
from src.services.jwt_service import JWTService

class MailService:

    @staticmethod
    def send_verification_email(user: User):
        token = JWTService.generate_email_token(user.email)
        verify_url = url_for('account.verify_email', token=token, _external=True)

        msg = Message(
            subject='Verify your email address',
            recipients=[user.email],
            body=f'Click the link to verify your email: {verify_url}'
        )
        mail.send(msg)