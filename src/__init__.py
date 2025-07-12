from flask import Flask
from .extensions import csrf
from dotenv import load_dotenv
from src.db.models import User
from src.db import init_db, get_db_session
from src.routes import dashboard, project, notes, sub_project, milestone, auth, home, about, revision, account, \
    webhooks, journal, venue, academia, admin
import os
from datetime import datetime, timezone
from flask_login import LoginManager
import stripe
from multiprocessing import Process, Event
from src.tasks.downgrade_users import run_downgrade_loop
from .extensions import mail
import logging
from src.utils.logging_config import setup_logging

logger = logging.getLogger(__name__)

_shutdown_event = Event()
_downgrade_process = None

stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')


def create_app() -> Flask:
    load_dotenv()

    app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), 'templates'))
    app.secret_key = os.environ.get("APP_SECRET", "default_secret")
    app.jinja_env.globals['now'] = int(datetime.now(timezone.utc).timestamp() * 1000)
    csrf.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"  # Redirect unauthorized users here


    db_session = get_db_session()

    # Register blueprints
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(project.bp)
    app.register_blueprint(notes.bp)
    app.register_blueprint(sub_project.bp)
    app.register_blueprint(milestone.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(home.bp)
    app.register_blueprint(about.bp)
    app.register_blueprint(revision.bp)
    app.register_blueprint(account.bp)
    app.register_blueprint(webhooks.bp)
    app.register_blueprint(journal.bp)
    app.register_blueprint(venue.bp)
    app.register_blueprint(academia.bp)
    app.register_blueprint(admin.bp)

    app.config.update(
        MAIL_SERVER='mail.smtp2go.com',
        MAIL_PORT=587,
        MAIL_USE_TLS=True,
        MAIL_USERNAME=os.environ.get('SMTP2GO_USER'),
        MAIL_PASSWORD=os.environ.get('SMTP2GO_PASSWORD'),
        MAIL_DEFAULT_SENDER='noreply@anobrain.ai'
    )

    mail.init_app(app)

    # Cleanup SQLAlchemy session after each request
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        db_session.remove()

    @app.template_filter('datetimeformat')
    def datetimeformat(value, format="%Y-%m-%d %H:%M"):
        try:
            return datetime.fromtimestamp(value / 1000).strftime(format)
        except Exception as e:
            return "Invalid timestamp"

    @app.template_filter('dateformat')
    def dateformat(value, format="%Y-%m-%d"):
        try:
            return datetime.fromtimestamp(value / 1000).strftime(format)
        except Exception as e:
            return "Invalid timestamp"

    @app.template_filter('planFormat')
    def plan_format(value):
        """
        Formats plan names like 'student_plus' → 'Student+'
        """
        if not isinstance(value, str):
            return value
        return value.replace("_plus", "+").replace("_", " ").title()

    @login_manager.user_loader
    def load_user(user_id):
        return db_session.get(User, int(user_id))  # or get_db_session.query(User).get(int(user_id))

    return app


def start_background_downgrade_process():
    global _downgrade_process
    _downgrade_process = Process(target=run_downgrade_loop, args=(_shutdown_event,))
    _downgrade_process.start()
    logger.info(f"[Flask] Started background downgrade process with PID {_downgrade_process.pid}")


def stop_background_downgrade_process():
    global _downgrade_process
    if _downgrade_process is not None:
        logger.info("[Flask] Shutting down background downgrade process...")
        _shutdown_event.set()
        _downgrade_process.join(timeout=10)
        if _downgrade_process.is_alive():
            logger.info("[Flask] Background process did not shut down in time.")
        else:
            logger.info("[Flask] Background process shut down cleanly.")
