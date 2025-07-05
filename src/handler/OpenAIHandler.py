import json
from sqlalchemy.orm import Session
from src.plans import StripeMeter
from src.services.openai_service import OpenAIService
from src.db.models import Project, User
from src.services.log_service import AILogService
import stripe


class OpenAIHandler:

    @staticmethod
    def get_poster_requirements(db_session: Session, project_id: int, conference_name: str, user_id: int)-> bool:
        """
        Handler function to be called from the route to get poster requirements in a background thread
        :param db_session:
        :param conference_name:
        :param project_id:
        :param user_id:
        :return:
        """
        try:
            print("🔄 Fetching poster requirements for:", conference_name)
            json_response, usage = OpenAIService.get_poster_requirements(conference_name=conference_name)
            print(json_response)
            token_count = usage.get("total_tokens", 0)
            # log AI usage
            AILogService.log_ai_usage(session=db_session, user_id=user_id, event_name="journal_requirements",
                                      used_tokens=token_count)

            stripe.billing.MeterEvent.create(
                event_name=StripeMeter.TokenRequests.value,
                payload={
                    "value": str(token_count),
                    "stripe_customer_id": db_session.query(User).filter_by(id=user_id).first().stripe_customer_id,
                }
            )

            # 🔁 Re-fetch project safely inside this session/thread
            project: Project = db_session.query(Project).filter_by(id=project_id, user_id=user_id).first()
            if project:
                project.venue_requirements_data = json_response
                db_session.commit()
                print("✅ Venue requirements updated successfully.")
                return True
            else:
                print("❌ Project not found or doesn't belong to user.")
                return False
        except Exception as e:
            db_session.rollback()
            print(f"❌ Error while calling LLM: {e}")
            return False

    @staticmethod
    def get_journal_requirements(db_session: Session, project_id: int, journal_name: str, user_id: int) -> bool:
        """
        Handler function to be called from the route to get journal requirements in a background thread
        :param db_session:
        :param journal_name:
        :param project_id:
        :param user_id:
        :return:
        """
        try:
            print("🔄 Fetching journal requirements for:", journal_name)
            json_response, usage = OpenAIService.get_journal_requirements(journal_name=journal_name)
            print(json_response)
            token_count = usage.get("total_tokens", 0)
            # log AI usage
            AILogService.log_ai_usage(session=db_session, user_id=user_id, event_name="journal_requirements",
                                      used_tokens=token_count)

            stripe.billing.MeterEvent.create(
                event_name=StripeMeter.TokenRequests.value,
                payload={
                    "value": str(token_count),
                    "stripe_customer_id": db_session.query(User).filter_by(id=user_id).first().stripe_customer_id,
                }
            )

            # 🔁 Re-fetch project safely inside this session/thread
            project = db_session.query(Project).filter_by(id=project_id, user_id=user_id).first()
            if project:
                project.venue_requirements = json.dumps(json_response)
                db_session.commit()
                print("✅ Venue requirements updated successfully.")
                return True
            else:
                print("❌ Project not found or doesn't belong to user.")
            return False
        except Exception as e:
            db_session.rollback()
            print(f"❌ Error while calling LLM: {e}")
            return False
