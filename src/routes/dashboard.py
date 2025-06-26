from flask import Blueprint, render_template
from src.db.models import Milestone, Project
from src import db_session

bp = Blueprint('dashboard', __name__)


@bp.route("/")
def dashboard():
    try:
        projects = db_session.query(Project).order_by(Project.id.desc()).all()
        return render_template("dashboard.html", projects=projects)
    except Exception as e:
        print("Error loading dashboard:", e)
        return render_template("dashboard.html", projects=[], error="Something went wrong loading projects.")