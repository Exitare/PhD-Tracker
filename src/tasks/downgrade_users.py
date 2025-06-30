from datetime import datetime, timezone
from time import sleep
from src import db_session
from src.db.models import User

def downgrade_expired_users():
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    expired_users = db_session.query(User).filter(
        User.stripe_subscription_expires_at < now_ms,
        User.plan != "student"
    ).all()

    for user in expired_users:
        user.plan = "student"

    if expired_users:
        db_session.commit()
        print(f"[AutoDowngrade] Downgraded {len(expired_users)} users.")
    else:
        print("[AutoDowngrade] No users to downgrade.")

def run_downgrade_loop(shutdown_event, interval_seconds=300):
    print("[AutoDowngrade] Worker started.")
    try:
        while not shutdown_event.is_set():
            downgrade_expired_users()
            shutdown_event.wait(timeout=interval_seconds)
    finally:
        db_session.remove()
        print("[AutoDowngrade] Worker exiting and cleaned up DB session.")