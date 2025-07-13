from src.db.models import User
from flask import url_for
from flask_mail import Message
from src.extensions import mail
from src.services.jwt_service import JWTService
import threading
from flask import current_app
import os

mode: str = os.getenv('MODE', 'dev')


class MailService:
    @staticmethod
    def _send_async_email(app, msg):
        with app.app_context():
            mail.send(msg)

    @staticmethod
    def send_password_updated_email(user):
        msg = Message(
            subject='Your password has been updated',
            recipients=[user.email],
            body='Your password has been successfully updated.'
        )

        # Launch in a background thread
        threading.Thread(
            target=MailService._send_async_email,
            args=(current_app._get_current_object(), msg),
            daemon=True  # Optional: daemon=True ends the thread with the main process
        ).start()

    @staticmethod
    def send_password_reset_email(user: User):
        token = JWTService.generate_password_reset_token(user=user)
        reset_url = url_for('auth.reset_password', token=token, _external=True)

        msg = Message(
            subject='Your password reset link',
            recipients=[user.email],
            body='To reset your password, click the link below:\n' + reset_url
        )

        # Launch in a background thread
        threading.Thread(
            target=MailService._send_async_email,
            args=(current_app._get_current_object(), msg),
            daemon=True  # Optional: daemon=True ends the thread with the main process
        ).start()

    @staticmethod
    def send_verification_email(user: User):
        token = JWTService.generate_email_token(user=user)
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

    @staticmethod
    def send_academia_confirmation_email(user):
        msg = Message(
            subject='Academia Registration Confirmation',
            recipients=[user.email],
            body=f'Thank you for registering, {user.first_name}!.'
        )

        # Launch in a background thread
        threading.Thread(
            target=MailService._send_async_email,
            args=(current_app._get_current_object(), msg),
            daemon=True  # Optional: daemon=True ends the thread with the main process
        ).start()

    @staticmethod
    def send_payment_failed_email(user):
        msg = Message(
            subject='Payment Failed',
            recipients=[user.email],
            body="Your recent payment attempt has failed. Please update your payment information. If you have any questions, contact support."
        )

        # Launch in a background thread
        threading.Thread(
            target=MailService._send_async_email,
            args=(current_app._get_current_object(), msg),
            daemon=True  # Optional: daemon=True ends the thread with the main process
        ).start()

    @staticmethod
    def send_academia_inquiry_email(first_name: str, last_name: str, email: str, num_students: int,
                                    additional_information: str, phone_number: str,
                                    organization: str):
        msg = Message(
            subject='Academia Inquiry Received',
            recipients=["contact@anobrain.ai" if mode != "dev" else "raphael.kirchgaessner@anobrain.ai"],
            body=f'We have received an inquiry from {first_name} {last_name}.\n' +
                 f'Organization: {organization}\n' +
                 f'Number of Students: {num_students}\n' +
                 f'Information: {additional_information}\n' +
                 f'Email: {email}, Phone: {phone_number}\n'
        )

        # Launch in a background thread
        threading.Thread(
            target=MailService._send_async_email,
            args=(current_app._get_current_object(), msg),
            daemon=True  # Optional: daemon=True ends the thread with the main process
        ).start()

        msg = Message(
            subject='Your Academia Inquiry has been received',
            recipients=[email],
            body=f'Thank you for your inquiry, {first_name} {last_name}.\n' +
                 f'We will get back to you shortly regarding your request for {num_students} students at {organization}.\n' +
                 'If you have any further questions, feel free to reach out. Thank you for your interest in AnoBrain Academia!'
        )

        # Launch in a background thread
        threading.Thread(
            target=MailService._send_async_email,
            args=(current_app._get_current_object(), msg),
            daemon=True  # Optional: daemon=True ends the thread with the main process
        ).start()
