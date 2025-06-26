from flask import Flask
from flask_wtf import CSRFProtect
from dotenv import load_dotenv
from src.db import init_db, db_session
from src.routes import dashboard, project, notes, sub_project, milestone
import os
from datetime import datetime, timezone

csrf = CSRFProtect()


def create_app():
    load_dotenv()

    app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), 'templates'))
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", "default_secret")
    csrf.init_app(app)

    # Initialize database tables (runs once)
    init_db()

    # Register blueprints
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(project.bp)
    app.register_blueprint(notes.bp)
    app.register_blueprint(sub_project.bp)
    app.register_blueprint(milestone.bp)

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

    return app
