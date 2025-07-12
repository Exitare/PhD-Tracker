from flask import Blueprint, render_template

bp = Blueprint('plans', __name__)


@bp.route("/plans", methods=["GET"])
def plans():
    return render_template('plans.html')
