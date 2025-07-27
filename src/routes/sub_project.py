from quart import Blueprint, render_template, redirect, url_for, request, abort, flash, jsonify
from datetime import datetime, timezone
from src.db.models import SubProject, Milestone, Project
from src.db import get_db_session
from src.services.openai_service import OpenAIService
from quart_auth import login_required, current_user
from src.services import AILogService, UserService
from src.role import Role
from sqlalchemy import func

bp = Blueprint('subproject', __name__)


@bp.route("/dashboard/projects/<int:project_id>/subprojects/create", methods=["GET"])
@login_required
async def show_sub_project_form(project_id: int):
    if not UserService.can_access_page(current_user, allowed_roles=[Role.User.value]):
        await flash("You do not have permission to view this page.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    db_session = get_db_session()
    try:
        project = db_session.query(Project).filter_by(id=project_id, user_id=current_user.id).first()
        if not project:
            return await render_template("dashboard.html", projects=[], error="Project not found.")

        return await render_template("create-sub-project.html", project=project, now=datetime.now(timezone.utc))
    except Exception as e:
        print("Error loading project for subproject creation:", e)
        return await render_template("dashboard.html", projects=[], error="Failed to load project. Please try again.")


@bp.route("/dashboard/projects/<int:project_id>/subprojects", methods=["POST"])
@login_required
async def create(project_id: int):
    if not UserService.can_access_page(current_user, allowed_roles=[Role.User.value]):
        await flash("You do not have permission to view this page.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    db_session = get_db_session()
    try:
        project = db_session.query(Project).filter_by(id=project_id).first()
        # Ensure the project exists and belongs to the current user
        if not project or project.user_id != current_user.id:
            return await render_template("dashboard.html", projects=[], error="Project not found.")

    except Exception as e:
        print("Error loading project for subproject creation:", e)
        return redirect(url_for("dashboard.dashboard"))

    try:

        title = form.get("title", "").strip()
        description = form.get("description", "").strip()
        ai_option = form.get("ai_option", "")
        deadline = form.get("deadline", "").strip()
        sub_project_type: str = form.get("type", "default").strip()

        print("Creating subproject with title:", title)

        if not title or not description or not deadline:
            return await render_template("project-detail.html", project_id=project_id, project=project,
                                   error="All fields are required", now=datetime.now(timezone.utc))

        if ai_option == "yes" and not UserService.can_use_ai(current_user):
            return await render_template("project-detail.html", project_id=project_id, project=project,
                                   error="AI-generated milestones are not only available for Student accounts.",
                                   now=datetime.now(timezone.utc))

        deadline_str = form.get("deadline", "").strip()
        try:
            deadline_date = datetime.strptime(deadline_str, "%Y-%m-%d").date()
            if deadline_date < datetime.now(timezone.utc).date():
                return await render_template("project-detail.html", project_id=project_id, project=project,
                                       error="Deadline cannot be earlier than today.")
        except ValueError:
            await flash("Invalid date format for deadline.", "danger")
            return redirect(url_for('subproject.show_sub_project_form', project_id=project.id))

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
            await flash("A goal with this title already exists.", "danger")
            return redirect(url_for('subproject.show_sub_project_form', project_id=project.id))

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
        if ai_option == "yes" and UserService.can_use_ai(current_user):
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
            UserService.report_ai_usage(user=current_user, token_count=token_count)

            AILogService.log_ai_usage(session=db_session, user_id=current_user.id,
                                      event_name="create_subproject_with_milestones",
                                      used_tokens=token_count)

        print("Subproject created:", title)
        db_session.commit()
        return redirect(url_for("project.view", project_id=project_id))

    except Exception as e:
        db_session.rollback()
        print("Database error:", e)
        return await render_template("project-detail.html", project_id=project_id, project=project,
                               error="Failed to add subproject. Please try again.", now=datetime.now(timezone.utc))


@bp.route("/dashboard/projects/<int:project_id>/subprojects/<int:subproject_id>", methods=["GET"])
@login_required
async def view(project_id: int, subproject_id: int):
    if not UserService.can_access_page(current_user, allowed_roles=[Role.User.value]):
        await flash("You do not have permission to view this page.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    db_session = get_db_session()
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

    return await render_template(
        "sub-project-detail.html",
        project=project,
        subproject=sub,
        milestones=milestones,
        now=datetime.now(timezone.utc)
    )


@bp.route("/dashboard/projects/<int:project_id>/subprojects/<int:subproject_id>", methods=["POST"])
@login_required
async def edit(project_id: int, subproject_id: int):
    if not UserService.can_access_page(current_user, allowed_roles=[Role.User.value]):
        await flash("You do not have permission to view this page.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    db_session = get_db_session()

    sub = db_session.query(SubProject).filter_by(id=subproject_id, project_id=project_id).first()
    if not sub:
        abort(404)

    title = form.get("title", "").strip()
    description = form.get("description", "").strip()
    sub_project_type = form.get("type", "normal").strip()

    if not title or not description:
        await flash("Title and description are required.", "danger")
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
        await flash("A subproject with this title already exists.", "danger")
        return redirect(url_for("project.view", project_id=project_id))

    sub.title = title
    sub.description = description
    sub.type = sub_project_type

    try:
        db_session.commit()
        await flash("Subproject updated successfully.", "success")
    except Exception as e:
        db_session.rollback()
        print("Error editing subproject:", e)
        await flash("An error occurred while saving the subproject.", "danger")

    return redirect(url_for("project.view", project_id=project_id))


@bp.route("/dashboard/projects/<int:project_id>/subprojects/<int:subproject_id>/delete", methods=["POST"])
@login_required
async def delete(project_id: int, subproject_id: int):
    if not UserService.can_access_page(current_user, allowed_roles=[Role.User.value]):
        await flash("You do not have permission to view this page.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    db_session = get_db_session()
    sub = db_session.query(SubProject).filter_by(id=subproject_id).first()
    if not sub:
        abort(404, description="Subproject not found")

    project_id = sub.project_id
    db_session.delete(sub)
    db_session.commit()
    return redirect(url_for("project.view", project_id=project_id))


@bp.route('/dashboard/projects/<int:project_id>/subprojects/check_title/', methods=['POST'])
@login_required
async def check_subproject_title(project_id: int):
    data = request.get_json()
    title = data.get("title", "").strip().lower()
    db_session = get_db_session()
    exists = db_session.query(SubProject).filter(
        SubProject.project_id == project_id,
        func.lower(SubProject.title) == title
    ).first() is not None

    return jsonify({"exists": exists})
