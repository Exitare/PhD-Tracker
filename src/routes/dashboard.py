from flask import Blueprint, render_template
from flask_login import login_required, current_user
from src.db.models import Milestone, Project
from src import db_session

bp = Blueprint('dashboard', __name__)


@bp.route("/dashboard")
@login_required
def dashboard():
    try:
        # Optional: only show the current user's projects
        projects = db_session.query(Project).filter_by(user_id=current_user.id).order_by(Project.id.desc()).all()
        return render_template("dashboard.html", projects=projects)
    except Exception as e:
        print("Error loading dashboard:", e)
        return render_template("dashboard.html", projects=[], error="Something went wrong loading projects.")