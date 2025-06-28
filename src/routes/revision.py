from datetime import datetime, timezone
from flask import Blueprint, request, redirect, render_template, url_for, abort, flash
from src.db.models import Project, SubProject, Milestone
from src import db_session
from werkzeug.utils import secure_filename
from flask_login import current_user, login_required
from pathlib import Path

from src.openai_client import OpenAIService

bp = Blueprint('revision', __name__, template_folder="templates/revision")


@bp.route("/dashboard/projects/<int:project_id>/revision/start", methods=["GET"])
@login_required
def start(project_id):
    # logic to show upload form and revision deadline
    return render_template("start.html", project_id=project_id)


@bp.route("/dashboard/projects/<int:project_id>/revision/start>", methods=["POST"])
@login_required
def submit(project_id: int):
    raw_text = request.form.get("raw_text", "").strip()
    deadline_str = request.form.get("deadline")

    if not raw_text:
        flash("Please paste reviewer comments into the text box.", "danger")
        return redirect(url_for("revision.start", project_id=project_id))

    if not deadline_str:
        flash("Please select a revision deadline.", "danger")
        return redirect(url_for("revision.start", project_id=project_id))

    try:
        deadline = datetime.strptime(deadline_str, "%Y-%m-%d").date()
    except ValueError:
        flash("Invalid date format for deadline.", "danger")
        return redirect(url_for("revision.start", project_id=project_id))

    if deadline < datetime.now(timezone.utc).date():
        flash("Revision deadline cannot be earlier than today.", "danger")
        return redirect(url_for("revision.start", project_id=project_id))

        # === Step 1: Call OpenAI to generate milestones ===
    milestones, usage_info = OpenAIService.submit_reviewer_feedback_milestone_generation(
        reviewer_text=raw_text,
        deadline=deadline_str
    )


    # === Step 2: Find next available revision title ===
    base_title = "Revision"
    existing_revisions = SubProject.query.filter_by(project_id=project_id).filter(
        SubProject.title.ilike(f"{base_title}%")
    ).count()
    revision_number = existing_revisions + 1
    subproject_title = f"{base_title} {revision_number}"

    # === Step 3: Create new subproject ===
    new_subproject = SubProject(
        project_id=project_id,
        title=subproject_title,
        description="Automatically generated revision plan based on reviewer feedback."
    )
    db_session.add(new_subproject)
    db_session.commit()

    # === Step 4: Save milestones to DB ===
    for m in milestones:
        milestone = Milestone(
            sub_project_id=new_subproject.id,
            milestone=m.milestone,
            due_date=m.due_date  # assumed to be a 'YYYY-MM-DD' string
            # notes and status will default automatically
        )
        db_session.add(milestone)

    db_session.commit()

    flash(f"{subproject_title} with {len(milestones)} milestones was created.", "success")
    return redirect(url_for("subproject.view", project_id=project_id, subproject_id=new_subproject.id))
