from flask import Blueprint, render_template, redirect, url_for, request, abort, flash
from datetime import datetime, timezone
from src.db.models import SubProject, Milestone, Project
from src import db_session
from src.services.openai_service import OpenAIService
from flask_login import login_required, current_user
import stripe
from src.plans import Plans, StripeMeter
from src.services.log_service import AILogService


bp = Blueprint('subproject', __name__)


@bp.route("/dashboard/projects/<int:project_id>/subprojects/create", methods=["GET"])
@login_required
def show_sub_project_form(project_id: int):
    try:
        project = db_session.query(Project).filter_by(id=project_id, user_id=current_user.id).first()
        if not project:
            return render_template("dashboard.html", projects=[], error="Project not found.")

        return render_template("create-sub-project.html", project=project, now=datetime.now(timezone.utc))
    except Exception as e:
        print("Error loading project for subproject creation:", e)
        return render_template("dashboard.html", projects=[], error="Failed to load project. Please try again.")

@bp.route("/dashboard/projects/<int:project_id>/subprojects", methods=["POST"])
@login_required
def create(project_id: int):
    try:
        project = db_session.query(Project).filter_by(id=project_id).first()
        # Ensure the project exists and belongs to the current user
        if not project or project.user_id != current_user.id:
            return render_template("dashboard.html", projects=[], error="Project not found.")

        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        ai_option = request.form.get("ai_option", "")
        deadline = request.form.get("deadline", "").strip()
        sub_project_type: str = request.form.get("type", "default").strip()

        print("Creating subproject with title:", title)

        if not title or not description or not deadline:
            return render_template("project-detail.html", project_id=project_id, project=project,
                                   error="All fields are required", now=datetime.now(timezone.utc))

        if ai_option == "yes" and current_user.plan != Plans.StudentPlus.value:
            return render_template("project-detail.html", project_id=project_id, project=project,
                                   error="AI-generated milestones are only available for Student+ accounts.",
                                   now=datetime.now(timezone.utc))

        deadline_str = request.form.get("deadline", "").strip()
        try:
            deadline_date = datetime.strptime(deadline_str, "%Y-%m-%d").date()
            if deadline_date < datetime.now(timezone.utc).date():
                return render_template("project-detail.html", project_id=project_id, project=project,
                                       error="Deadline cannot be earlier than today.")
        except ValueError:
            return render_template("project-detail.html", project_id=project_id, project=project,
                                   error="Invalid date format for deadline.")

        # check if the title already exists for the same user but different subproject
        duplicate = (
            db_session.query(SubProject)
            .join(Project)
            .filter(
                SubProject.title == title,
                Project.user_id == current_user.id,
                SubProject.project_id == project_id
            )
            .first()
        )

        if duplicate:
            flash("A subproject with this title already exists.", "danger")

            project = db_session.query(Project).filter_by(id=project_id).first()
            if not project or project.user_id != current_user.id:
                return render_template("dashboard.html", projects=[], error="Project not found.")

            subprojects = (
                db_session.query(SubProject)
                .filter_by(project_id=project_id)
                .all()
            )

            # For milestone counts
            subprojects_with_milestones = []
            for sub in subprojects:
                milestones = db_session.query(Milestone).filter_by(sub_project_id=sub.id).all()
                subprojects_with_milestones.append({
                    "subproject": sub,
                    "milestones": milestones
                })

            return render_template(
                "project-detail.html",
                project=project,
                subprojects=subprojects_with_milestones,
                now=datetime.now(timezone.utc)
            )

        new_subproject = SubProject(
            title=title,
            description=description,
            project_id=project_id,
            created_at=int(datetime.now(timezone.utc).timestamp() * 1000),
            type=sub_project_type,
            deadline=int(deadline_date.strftime("%s")) * 1000,  # Convert to milliseconds
        )
        db_session.add(new_subproject)
        db_session.flush()  # Needed to get new_subproject.id before commit

        # If AI is requested, generate and add milestones
        if ai_option == "yes" and current_user.plan == Plans.StudentPlus.value:
            print("Generating milestones using AI...")
            ai_milestones, usage = OpenAIService.generate_milestones(title, deadline)
            for ai_m in ai_milestones:
                db_milestone = Milestone(
                    sub_project_id=new_subproject.id,
                    milestone=ai_m.milestone,
                    due_date=ai_m.due_date,
                )
                db_session.add(db_milestone)
            print(f"{len(ai_milestones)} AI milestones created.")

            token_count = usage.get("total_tokens", 0)
            print(f"AI token usage: {token_count}")
            # report usage
            stripe.billing.MeterEvent.create(
                event_name=StripeMeter.TokenRequests.value,
                payload={
                    "value": str(token_count),
                    "stripe_customer_id": current_user.stripe_customer_id,
                }
            )

            AILogService.log_ai_usage(session=db_session, user_id=current_user.id, event_name="create_subproject_with_milestones",
                                      used_tokens=token_count)

        print("Subproject created:", title)
        db_session.commit()
        return redirect(url_for("project.view", project_id=project_id))

    except Exception as e:
        db_session.rollback()
        print("Database error:", e)
        return render_template("project-detail.html", project_id=project_id,
                               error="Failed to add subproject. Please try again.", now=datetime.now(timezone.utc))


@bp.route("/dashboard/projects/<int:project_id>/subprojects/<int:subproject_id>", methods=["GET"])
@login_required
def view(project_id: int, subproject_id: int):
    sub = db_session.query(SubProject).filter_by(id=subproject_id, project_id=project_id).first()
    if not sub:
        abort(404, description="Subproject not found")

    milestones = (
        db_session.query(Milestone)
        .filter_by(sub_project_id=subproject_id)
        .order_by(Milestone.due_date.asc())
        .all()
    )

    project = db_session.query(Project).filter_by(id=project_id).first()
    if not project:
        abort(404, description="Project not found")

    return render_template(
        "sub-project-detail.html",
        project=project,
        subproject=sub,
        milestones=milestones,
        now=datetime.now(timezone.utc)
    )


@bp.route("/dashboard/projects/<int:project_id>/subprojects/<int:subproject_id>", methods=["POST"])
@login_required
def edit(project_id: int, subproject_id: int):
    sub = db_session.query(SubProject).filter_by(id=subproject_id, project_id=project_id).first()
    if not sub:
        abort(404)

    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()

    if not title or not description:
        flash("Title and description are required.", "danger")
        return redirect(url_for("project.view", project_id=project_id))

    # Check if the new title already exists for the same user but different subproject
    duplicate = (
        db_session.query(SubProject)
        .join(Project)
        .filter(
            SubProject.title == title,
            SubProject.id != sub.id,
            Project.user_id == current_user.id
        )
        .first()
    )
    if duplicate:
        flash("A subproject with this title already exists.", "danger")
        return redirect(url_for("project.view", project_id=project_id))

    sub.title = title
    sub.description = description

    try:
        db_session.commit()
        flash("Subproject updated successfully.", "success")
    except Exception as e:
        db_session.rollback()
        print("Error editing subproject:", e)
        flash("An error occurred while saving the subproject.", "danger")

    return redirect(url_for("project.view", project_id=project_id))


@bp.route("/dashboard/projects/<int:project_id>/subprojects/<int:subproject_id>/delete", methods=["POST"])
@login_required
def delete(project_id: int, subproject_id: int):
    sub = db_session.query(SubProject).filter_by(id=subproject_id).first()
    if not sub:
        abort(404, description="Subproject not found")

    project_id = sub.project_id
    db_session.delete(sub)
    db_session.commit()
    return redirect(url_for("project.view", project_id=project_id))
