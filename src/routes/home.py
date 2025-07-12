from flask import Blueprint, render_template, session

bp = Blueprint('home', __name__)


@bp.route("/")
def home():
    if 'theme' not in session:
        session['theme'] = "lavender-dark"
    return render_template('home.html')
