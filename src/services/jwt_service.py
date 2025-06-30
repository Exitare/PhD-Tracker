from datetime import datetime, timedelta, timezone
from flask import current_app
import jwt

class JWTService:

    @staticmethod
    def generate_email_token(email: str) -> str:
        payload = {
            "email": email,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
            "iat": datetime.now(timezone.utc),
        }
        return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")

    @staticmethod
    def verify_email_token(token: str) -> str | None:
        try:
            payload = jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])
            return payload["email"]
        except jwt.ExpiredSignatureError:
            return None  # Token expired
        except jwt.InvalidTokenError:
            return None  # Invalid token
