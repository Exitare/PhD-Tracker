from flask import Blueprint, request, jsonify
from src.models import Milestone
from src import db_session
from flask_wtf.csrf import validate_csrf
from wtforms.validators import ValidationError

bp = Blueprint('notes', __name__)


@bp.route("/dashboard/projects/<int:project_id>/milestones/<int:milestone_id>/note", methods=["GET"])
def get_note(project_id, milestone_id):
    milestone = db_session.query(Milestone).filter_by(id=milestone_id).first()
    return jsonify(note=milestone.notes if milestone else "")


@bp.route("/dashboard/projects/<int:project_id>/milestones/<int:milestone_id>/note", methods=["POST"])
def save_note(project_id, milestone_id):
    csrf_token = request.headers.get("X-CSRFToken")
    try:
        validate_csrf(csrf_token)
    except ValidationError:
        return jsonify(success=False, message="Invalid CSRF token."), 400

    data = request.get_json()
    note = data.get("note", "")

    try:
        milestone = db_session.query(Milestone).filter_by(id=milestone_id).first()
        if not milestone:
            return jsonify(success=False, message="Milestone not found."), 404

        milestone.notes = note
        db_session.commit()
        print(f"Note saved for milestone {milestone_id}: {note}")
        return jsonify(success=True)
    except Exception as e:
        print("Database error:", e)
        db_session.rollback()
        return jsonify(success=False, message="Failed to save note. Please try again."), 500