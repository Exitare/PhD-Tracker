from sqlalchemy.orm import Session
from src.services import OpenAIService, UserService, AILogService
from src.db.models import Project, User
import logging

logger = logging.getLogger(__name__)


class OpenAIHandler:

    @staticmethod
    def get_venue_requirements(db_session: Session, project: Project, venue_name: str, user_id: int) -> bool:

        if project.type == 'poster':
            try:
                json_response, usage = OpenAIService.get_poster_requirements(conference_name=venue_name)
            except Exception as e:
                logger.exception(f"Error fetching poster requirements: {e}")
                return False
        elif project.type == 'paper':
            try:
                json_response, usage = OpenAIService.get_journal_requirements(journal_name=venue_name)
            except Exception as e:
                logger.exception(f"Error fetching journal requirements: {e}")
                return False

        else:
            print("❌ Unsupported project type for venue requirements.")
            return False

        logger.debug("🔄 Fetched venue requirements for:", venue_name)
        logger.debug(json_response)

        current_user: User | None = db_session.query(User).filter_by(id=user_id).first()
        if not current_user:
            logger.warning("❌ User not found.")
            return False

        token_count = usage.get("total_tokens", 0)
        # log AI usage
        AILogService.log_ai_usage(session=db_session, user_id=user_id, event_name="journal_requirements",
                                  used_tokens=token_count)

        UserService.report_ai_usage(user=current_user, token_count=token_count)

        # 🔁 Re-fetch project safely inside this session/thread
        project: Project | None = db_session.query(Project).filter_by(id=project.id, user_id=user_id).first()
        if project:
            project.venue_requirements_data = json_response
            db_session.commit()
            logger.info("✅ Venue requirements updated successfully.")
            return True
        else:
            logger.error("❌ Project not found or doesn't belong to user.")
            return False

