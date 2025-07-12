from datetime import datetime, timezone
from src.role import Role
from src import db_session
from src.db.models import User
from src.plans import Plans
import logging
from src.utils.logging_config import setup_logging
logger = logging.getLogger(__name__)


def downgrade_expired_users():
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    expired_users = db_session.query(User).filter(
        User.stripe_subscription_expires_at < now_ms,
        User.plan != Plans.Student.value,
    ).all()

    user: User
    for user in expired_users:
        user.plan = Plans.Student.value
        user.stripe_subscription_id = None
        user.stripe_subscription_item_ids = None
        user.stripe_subscription_expires_at = None
        user.stripe_subscription_canceled = False

        if user.role == Role.Manager.value:
            # Downgrade managed users as well
            managed_users = db_session.query(User).filter_by(managed_by=user.id).all()
            for managed_user in managed_users:
                managed_user.plan = Plans.Student.value
                managed_user.stripe_subscription_id = None
                managed_user.stripe_subscription_item_ids = None
                managed_user.stripe_subscription_expires_at = None
                managed_user.stripe_subscription_canceled = False

    if expired_users:
        db_session.commit()
        print(f"[AutoDowngrade] Downgraded {len(expired_users)} users to Student plan.")
    else:
        logger.info("[AutoDowngrade] No users to downgrade.")

def run_downgrade_loop(shutdown_event, interval_seconds=300):
    setup_logging(console_level=logging.INFO)  # <<< ADD THIS LINE
    logger.info("[AutoDowngrade] Worker started.")
    try:
        while not shutdown_event.is_set():
            downgrade_expired_users()
            shutdown_event.wait(timeout=interval_seconds)
    finally:
        db_session.remove()
        logger.info("[AutoDowngrade] Worker exiting and cleaned up DB session.")