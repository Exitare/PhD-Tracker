from flask import Blueprint, request, redirect, url_for, abort, jsonify
from src.db.models import Milestone
from src import db_session
from sqlalchemy.exc import SQLAlchemyError

bp = Blueprint('milestone', __name__)


@bp.route("/dashboard/projects/<int:project_id>/subprojects/<int:subproject_id>/milestones", methods=["POST"])
def create(project_id: int, subproject_id: int):
    form = request.form
    milestone = Milestone(
        sub_project_id=subproject_id,
        milestone=form["milestone"],
        due_date=form.get("due_date") or "",
        status=form.get("status") or "Not Started",
        notes=""
    )
    db_session.add(milestone)
    db_session.commit()
    return redirect(
        url_for("subproject.view", project_id=milestone.sub_project.project_id, subproject_id=subproject_id))


@bp.route("/dashboard/projects/<int:project_id>/subprojects/<int:subproject_id>/milestones/<int:milestone_id>",
          methods=["POST"])
def update(project_id: int, subproject_id: int, milestone_id: int):
    form = request.form

    milestone = db_session.query(Milestone).filter_by(id=milestone_id, sub_project_id=subproject_id).first()
    if not milestone:
        abort(404, description="Milestone not found")

    milestone.milestone = form["milestone"]
    milestone.due_date = form.get("due_date") or ""
    milestone.status = form.get("status") or milestone.status  # optional
    db_session.commit()

    return redirect(
        url_for("subproject.view", project_id=project_id, subproject_id=subproject_id)
    )


@bp.route("/dashboard/projects/<int:project_id>/subprojects/<int:subproject_id>/milestones/<int:milestone_id>/status",
          methods=["POST"])
def update_status(project_id: int, subproject_id: int, milestone_id: int):
    status = request.form["status"]

    # Fetch milestone
    milestone = db_session.query(Milestone).filter_by(id=milestone_id, sub_project_id=subproject_id).first()
    if not milestone:
        abort(404, description="Milestone not found")

    # Update and save
    milestone.status = status
    db_session.commit()

    return redirect(url_for("subproject.view", project_id=project_id, subproject_id=subproject_id))


@bp.route("/dashboard/projects/<int:project_id>/subprojects/<int:subproject_id>/milestones/<int:milestone_id>",
          methods=["DELETE"])
def delete_milestone(project_id: int, subproject_id: int, milestone_id: int):
    print(f"Deleting milestone {milestone_id} for project {project_id}")

    milestone = db_session.query(Milestone).filter_by(id=milestone_id, sub_project_id=subproject_id).first()
    if not milestone:
        return jsonify(success=False, message="Milestone not found."), 404

    try:
        db_session.delete(milestone)
        db_session.commit()
        return jsonify(success=True, message="Milestone deleted successfully.")
    except SQLAlchemyError as e:
        print("Database error:", e)
        db_session.rollback()
        return jsonify(success=False, message="Failed to delete milestone. Please try again."), 500
