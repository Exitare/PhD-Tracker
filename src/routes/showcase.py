from datetime import datetime, timezone
from quart import Blueprint, request, redirect, render_template, url_for, abort, flash

from src.services import UserService

bp = Blueprint('showcase', __name__)

@bp.route('/showcase')
async def showcase():
    return await render_template('showcase/showcase.html')