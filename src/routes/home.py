from flask import Blueprint, render_template, session
from flask_login import login_required, current_user
from src.db.models import Milestone, Project
from src import db_session

bp = Blueprint('home', __name__)


@bp.route("/")
def home():
    if 'theme' not in session:
        session['theme'] = "lavender-dark"
    return render_template('home.html')
