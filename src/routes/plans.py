from quart import Blueprint, render_template

bp = Blueprint('plans', __name__)


@bp.route("/plans", methods=["GET"])
async def plans():
    return await render_template('plans.html')
