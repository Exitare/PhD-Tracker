from datetime import datetime, timezone
from quart import Blueprint, request, redirect, render_template, url_for, abort, flash
from src.db.models import Project, SubProject, Milestone
from src.db import get_db_session
from quart_auth import current_user, login_required
from src.role import Role

from src.services import UserService

bp = Blueprint('project', __name__)


@bp.route("/create-project", methods=["GET", "POST"])
@login_required
async def create_project():


    args = await request.args    form = await request.form    if not UserService.can_access_page(current_user, allowed_roles=[Role.User.value]):
        await flash("You do not have permission to create a project.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    db_session = get_db_session()
    if await request.method == "POST":
        title = form["title"]
        description = form["description"]
        project_type = form["type"]
        selected_venue = form["selected_venue"]
        selected_venue_url = form["selected_venue_url"]

        try:
            new_project: Project = Project(title=title,
                                           type=project_type,
                                           description=description,
                                           created_at=int(datetime.now(timezone.utc).timestamp() * 1000),
                                           user_id=current_user.id,
                                           selected_venue=selected_venue,
                                           selected_venue_url=selected_venue_url)
            db_session.add(new_project)
            db_session.commit()
            print("Created new project:", title)
            return redirect(url_for("dashboard.dashboard"))
        except Exception as e:
            db_session.rollback()
            print("Database error:", e)
            return await render_template("create-project.html", error="Failed to create project. Please try again.")

    return await render_template("create-project.html")


@bp.route("/dashboard/projects/<int:project_id>")
@login_required
async def view(project_id: int):
    if not UserService.can_access_page(current_user, allowed_roles=[Role.User.value]):
        await flash("You do not have permission to view this project.", "danger")
        return redirect(url_for("dashboard.dashboard"))


    try:
        db_session = get_db_session()
        # Load the project
        project = db_session.query(Project).filter_by(id=project_id).first()
        if not project:
            return await render_template("dashboard.html", projects=[], error="Project not found.")

        # Load subprojects + milestones related to the project
        # Get all subprojects with their milestones
        subprojects = []
        raw_subs = db_session.query(SubProject).filter_by(project_id=project_id).all()
        for sub in raw_subs:
            milestones = db_session.query(Milestone).filter_by(sub_project_id=sub.id).all()
            subprojects.append({
                "subproject": sub,
                "milestones": milestones
            })

        return await render_template(
            "project-detail.html",
            project=project,
            subprojects=subprojects,
            now=datetime.now()
        )
    except Exception as e:
        print("Error loading project:", e)
        return await render_template("dashboard.html", projects=[], error="Error loading project.")


@bp.route("/dashboard/projects/<int:project_id>", methods=["POST"])
@login_required
async def edit(project_id: int):
    if not UserService.can_access_page(current_user, allowed_roles=[Role.User.value]):
        await flash("You do not have permission to edit this project.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    db_session = get_db_session()
    project = db_session.query(Project).filter_by(id=project_id).first()
    if not project:
        abort(404)

    if project.user_id != current_user.id:
        abort(403)

    title = form.get("title", "").strip()
    description = form.get("description", "").strip()
    proj_type = form.get("type", "").strip()
    selected_venue = form.get("selected_venue", "").strip()
    selected_venue_url = form.get("selected_venue_url", "").strip()

    if not title or not description:
        await flash("Title and description are required.", "danger")
        return redirect(url_for("project.view", project_id=project_id))

    project.title = title
    project.description = description
    project.type = proj_type or None  # Optional
    project.selected_venue = selected_venue or None  # Optional
    project.selected_venue_url = selected_venue_url or None  # Optional

    db_session.commit()
    await flash("Project updated successfully.", "success")

    # Conditional redirect
    to_project: bool = args.get("to_project", "false").lower() == "true"
    if to_project:
        return redirect(url_for("project.view", project_id=project_id))
    else:
        return redirect(url_for("dashboard.dashboard"))


@bp.route("/dashboard/projects/<int:project_id>/delete", methods=["GET"])
@login_required
async def delete(project_id: int):
    if not UserService.can_access_page(current_user, allowed_roles=[Role.User.value]):
        await flash("You do not have permission to delete this project.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    db_session = get_db_session()
    project = db_session.query(Project).filter_by(id=project_id).first()
    if not project:
        await flash("Project not found.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    if project.user_id != current_user.id:
        await flash("You do not have permission to delete this project.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    try:
        db_session.delete(project)
        db_session.commit()
        await flash("Project deleted successfully.", "success")
    except Exception as e:
        db_session.rollback()
        print("Error deleting project:", e)
        await flash("Failed to delete project. Please try again.", "danger")

    return redirect(url_for("dashboard.dashboard"))
