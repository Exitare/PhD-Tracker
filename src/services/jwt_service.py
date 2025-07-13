import os
from collections import namedtuple
from datetime import datetime, timedelta, timezone
import jwt
import logging
from src.db.models import User

logger = logging.getLogger(__name__)

TokenPayload = namedtuple("TokenPayload", ["email", "id"])


class JWTService:

    @staticmethod
    def generate_email_token(user: User) -> str:
        payload = {
            "sub": str(user.id),
            "email": user.email,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
            "iat": datetime.now(timezone.utc),
        }
        return jwt.encode(payload, os.getenv("APP_SECRET"), algorithm="HS256")

    @staticmethod
    def generate_password_reset_token(user: User) -> str:
        print(os.getenv("APP_SECRET"))
        payload = {
            "sub": str(user.id),
            "email": user.email,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
            "iat": datetime.now(timezone.utc),
        }

        return jwt.encode(payload, os.getenv("APP_SECRET"), algorithm="HS256")

    @staticmethod
    def verify_token(token: str) -> TokenPayload | None:
        try:
            print(token)
            print(os.getenv("APP_SECRET"))
            payload = jwt.decode(token, os.getenv("APP_SECRET"), algorithms=["HS256"])
            return TokenPayload(id=int(payload.get("sub")), email=payload.get("email"))
        except jwt.ExpiredSignatureError:
            logger.debug("Expired token")
            return None
        except jwt.InvalidTokenError as e:
            logger.debug(e)
            logger.debug("Invalid token")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during token verification: {e}")
            return None
