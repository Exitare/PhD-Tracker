from quart import Blueprint, request, jsonify
from src.db.models import Milestone
from src.db import get_db_session
from flask_wtf.csrf import validate_csrf
from wtforms.validators import ValidationError
from sqlalchemy.exc import SQLAlchemyError

bp = Blueprint('notes', __name__)


@bp.route("/dashboard/projects/<int:project_id>/subprojects/<int:subproject_id>/milestones/<int:milestone_id>/note",
          methods=["GET"])
async def get_note(project_id: int, subproject_id: int, milestone_id: int):
    db_session = get_db_session()
    milestone = db_session.query(Milestone).filter_by(id=milestone_id).first()
    return jsonify(note=milestone.notes if milestone else "")


@bp.route("/dashboard/projects/<int:project_id>/subprojects/<int:subproject_id>/milestones/<int:milestone_id>/note",
          methods=["POST"])
async def save_note(project_id: int, subproject_id: int, milestone_id: int):
    csrf_token = request.headers.get("X-CSRFToken")

    try:
        validate_csrf(csrf_token)
    except ValidationError:
        print("Invalid CSRF token:", csrf_token)
        return jsonify(success=False, message="Invalid CSRF token."), 400

    data = request.get_json()
    note = data.get("note", "")
    db_session = get_db_session()
    try:

        milestone = db_session.query(Milestone).filter_by(id=milestone_id, sub_project_id=subproject_id).first()
        if not milestone:
            return jsonify(success=False, message="Milestone not found."), 404

        milestone.notes = note
        db_session.commit()

        print(f"Note saved for milestone {milestone_id}: {note}")
        return jsonify(success=True)

    except SQLAlchemyError as e:
        print("Database error in save_note:", e)
        db_session.rollback()
        return jsonify(success=False, message="Failed to save note. Please try again."), 500
