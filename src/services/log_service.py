from sqlalchemy.orm import Session
from src.db.models import UsageLog
import logging


class AILogService:

    @staticmethod
    def log_ai_usage(session: Session, user_id: int, event_name: str, used_tokens: int) -> bool:

        try:
            # Create a new log entry
            log_entry: UsageLog = UsageLog(user_id=user_id, used_tokens=used_tokens, event_name=event_name)
            session.add(log_entry)
            return True
        except Exception as e:
            logging.exception(f"[LogService] Error logging AI usage for user {user_id}: {e}")
            session.rollback()
            return False
