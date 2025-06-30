from src.db.models import User
from flask import url_for
from flask_mail import Message
from src.extensions import mail
from src.services.jwt_service import JWTService
import threading
from flask import current_app


class MailService:
    @staticmethod
    def _send_async_email(app, msg):
        with app.app_context():
            mail.send(msg)

    @staticmethod
    def send_verification_email(user):
        token = JWTService.generate_email_token(user.email)
        verify_url = url_for('account.verify_email', token=token, _external=True)

        msg = Message(
            subject='Verify your email address',
            recipients=[user.email],
            body=f'Click the link to verify your email: {verify_url}'
        )

        # Launch in a background thread
        threading.Thread(
            target=MailService._send_async_email,
            args=(current_app._get_current_object(), msg),
            daemon=True  # Optional: daemon=True ends the thread with the main process
        ).start()
