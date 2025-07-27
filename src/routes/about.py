from quart import Blueprint, render_template

bp = Blueprint('about', __name__)


@bp.route("/about")
async def about():
    return await render_template('about.html')