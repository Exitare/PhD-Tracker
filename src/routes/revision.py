from datetime import datetime, timezone
from flask import Blueprint, request, redirect, render_template, url_for, abort, flash
from src.db.models import Project, SubProject, Milestone
from src import db_session
from flask_login import current_user, login_required
from sqlalchemy import select
import stripe
from src.services.openai_service import OpenAIService, METER_NAME
from src.services.log_service import AILogService
from src.services import UserService
from src.role import Role

bp = Blueprint('revision', __name__)


@bp.route("/dashboard/projects/<int:project_id>/revision", methods=["GET"])
@login_required
def view(project_id):
    if not UserService.can_access_page(current_user, allowed_roles=[Role.User.value]):
        flash("You do not have permission to view a revision.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    try:
        stmt = select(Project).where(
            Project.id == project_id,
            Project.user_id == current_user.id
        )
        project = db_session.scalars(stmt).first()
        if not project:
            abort(404)
    except Exception as e:
        print("Error loading project:", e)
        flash("Failed to load project. Please try again.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    # logic to show upload form and revision deadline
    return render_template("revision/start.html", project_id=project_id, project=project)


@bp.route("/dashboard/projects/<int:project_id>/revision>", methods=["POST"])
@login_required
def create(project_id: int):
    if not UserService.can_access_page(current_user, [Role.User.value]):
        flash("You do not have permission to create a revision.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    raw_text = request.form.get("raw_text", "").strip()
    additional_context = request.form.get("additional_context", "").strip()
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

    milestones = []
    if UserService.can_use_ai(current_user):
        # ===Call OpenAI to generate milestones ===
        milestones, usage = OpenAIService.submit_reviewer_feedback_milestone_generation(
            reviewer_text=raw_text,
            deadline=deadline_str,
            additional_context=additional_context
        )

        if len(milestones) != 0:
            print(f"Generated {len(milestones)} milestones from OpenAI.")
            # report usage to the user
            token_count = usage.get("total_tokens", 0)
            print(f"AI token usage: {token_count}")
            # report usage
            UserService.report_usage(user=current_user, token_count=token_count)
            # log AI usage
            AILogService.log_ai_usage(
                session=db_session,
                user_id=current_user.id,
                event_name="revision_milestone_generation",
                used_tokens=token_count
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
        description="Automatically generated revision plan based on reviewer feedback.",
        created_at=int(datetime.now(timezone.utc).timestamp() * 1000),
        type="revision"
    )
    db_session.add(new_subproject)
    db_session.commit()

    # === Step 4: Save milestones to DB ===
    if len(milestones) != 0:
        for m in milestones:
            milestone = Milestone(
                sub_project_id=new_subproject.id,
                milestone=m.milestone,
                due_date=m.due_date  # assumed to be a 'YYYY-MM-DD' string
            )
            db_session.add(milestone)

    db_session.commit()

    flash(f"{subproject_title} with {len(milestones)} milestones was created.", "success")
    return redirect(url_for("subproject.view", project_id=project_id, subproject_id=new_subproject.id))
