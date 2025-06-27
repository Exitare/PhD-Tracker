from flask import Blueprint, render_template
from flask_login import login_required, current_user
from src.db.models import Milestone, Project
from src import db_session

bp = Blueprint('about', __name__)


@bp.route("/about")
def about():
    return render_template('about.html')