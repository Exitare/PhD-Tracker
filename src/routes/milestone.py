from flask import Blueprint, request, redirect, url_for, abort, jsonify, flash, render_template
from datetime import datetime
from src.db.models import Milestone, SubProject
from flask_login import current_user, login_required
from src import db_session
from sqlalchemy.exc import SQLAlchemyError
from typing import List
import stripe
from src.openai_client import OpenAIService

bp = Blueprint('milestone', __name__)


@bp.route("/dashboard/projects/<int:project_id>/subprojects/<int:subproject_id>/milestones", methods=["GET"])
def view(project_id: int, subproject_id: int):
    # Get the subproject and check if it exists
    subproject = db_session.query(SubProject).filter_by(id=subproject_id, project_id=project_id).first()

    # Check if subproject exists and belongs to the current user
    if not subproject or subproject.project.user_id != current_user.id:
        flash("Subproject not found or access denied.", "danger")
        return redirect(url_for("dashboard"))

    return render_template("create-milestone.html", project_id=project_id, subproject_id=subproject_id,
                           subproject=subproject)


@bp.route("/dashboard/projects/<int:project_id>/subprojects/<int:subproject_id>/milestones", methods=["POST"])
def create(project_id: int, subproject_id: int):
    form = request.form
    milestone_text = form.get("milestone", "").strip()
    due_date_str = form.get("due_date", "").strip()
    status = form.get("status", "Not Started").strip()

    # Check all fields
    if not milestone_text or not due_date_str:
        flash("All fields are required.", "danger")
        return redirect(url_for("subproject.view", project_id=project_id, subproject_id=subproject_id))

    # Validate date
    try:
        due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
        if due_date < datetime.today().date():
            flash("Due date cannot be in the past.", "danger")
            return redirect(url_for("subproject.view", project_id=project_id, subproject_id=subproject_id))
    except ValueError:
        flash("Invalid date format.", "danger")
        return redirect(url_for("subproject.view", project_id=project_id, subproject_id=subproject_id))

    # Create and save milestone
    milestone = Milestone(
        sub_project_id=subproject_id,
        milestone=milestone_text,
        due_date=due_date_str,
        status=status,
        notes=""
    )
    db_session.add(milestone)
    db_session.commit()

    return redirect(url_for("subproject.view", project_id=project_id, subproject_id=subproject_id))


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


@bp.route("/dashboard/projects/<int:project_id>/subprojects/<int:subproject_id>/milestones/refine", methods=["POST"])
@login_required
def refine(project_id: int, subproject_id: int):
    if current_user.plan != "StudentPlus":
        flash("This feature is only available for Student Plus plan users.", "danger")
        return redirect(url_for('dashboard.dashboard'))

    context: str = request.form.get("context", "")
    subproject: SubProject = db_session.query(SubProject).filter_by(id=subproject_id, project_id=project_id).first()
    if not subproject or subproject.project.user_id != current_user.id:
        return redirect(url_for('dashboard.dashboard'))

    existing_milestones: List[Milestone] = db_session.query(Milestone).filter_by(sub_project_id=subproject_id).all()
    # convert deadline to a string for LLM processing

    deadline_str = datetime.fromtimestamp(subproject.deadline / 1000).strftime("%Y-%m-%d")

    # 👇 Generate improved milestones via LLM
    milestones, usage = OpenAIService.refine_milestones(project_description=subproject.project.description,
                                                        subproject_description=subproject.description,
                                                        milestones=existing_milestones, additional_user_context=context,
                                                        deadline=deadline_str)

    token_count = usage.get("total_tokens", 0)
    print(f"AI token usage: {token_count}")
    # report usage
    stripe.billing.MeterEvent.create(
        event_name="tokenrequests",
        payload={
            "value": str(token_count),
            "stripe_customer_id": current_user.stripe_customer_id,
        }
    )

    # Fine milestones based on Milestone ids
    existing_ids = {m.id for m in existing_milestones}

    for m in milestones:
        if m.id in existing_ids:
            print(f"Updating existing milestone {m.id} with new data: {m.milestone}, {m.due_date}")
            # Update existing milestone
            db_milestone = db_session.query(Milestone).filter_by(id=m.id, sub_project_id=subproject_id).first()
            if db_milestone:
                db_milestone.milestone = m.milestone
                db_milestone.due_date = m.due_date
        else:
            print(f"Creating new milestone with data: {m.milestone}, {m.due_date}")
            # Create new milestone
            db_milestone = Milestone(
                sub_project_id=subproject_id,
                milestone=m.milestone,
                due_date=m.due_date,
            )
            db_session.add(db_milestone)

    db_session.commit()

    # Reload the subproject view
    return redirect(url_for("subproject.view", project_id=project_id, subproject_id=subproject_id))
