from datetime import datetime, timezone
from flask import Blueprint, request, redirect, render_template, url_for, abort, flash

from src.services import UserService

bp = Blueprint('showcase', __name__)

@bp.route('/showcase')
def showcase():
    return render_template('showcase/showcase.html')