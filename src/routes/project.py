from datetime import datetime, timezone
from flask import Blueprint, request, redirect, render_template, url_for, abort, flash
from src.db.models import Project, SubProject, Milestone
from src.db import get_db_session
from flask_login import current_user, login_required
from src.role import Role

from src.services import UserService

bp = Blueprint('project', __name__)


@bp.route("/create-project", methods=["GET", "POST"])
@login_required
def create_project():
    if not UserService.can_access_page(current_user, allowed_roles=[Role.User.value]):
        flash("You do not have permission to create a project.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    db_session = get_db_session()
    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]
        project_type = request.form["type"]
        selected_venue = request.form["selected_venue"]
        selected_venue_url = request.form["selected_venue_url"]

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
            return render_template("create-project.html", error="Failed to create project. Please try again.")

    return render_template("create-project.html")


@bp.route("/dashboard/projects/<int:project_id>")
@login_required
def view(project_id: int):
    if not UserService.can_access_page(current_user, allowed_roles=[Role.User.value]):
        flash("You do not have permission to view this project.", "danger")
        return redirect(url_for("dashboard.dashboard"))


    try:
        db_session = get_db_session()
        # Load the project
        project = db_session.query(Project).filter_by(id=project_id).first()
        if not project:
            return render_template("dashboard.html", projects=[], error="Project not found.")

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

        return render_template(
            "project-detail.html",
            project=project,
            subprojects=subprojects,
            now=datetime.now()
        )
    except Exception as e:
        print("Error loading project:", e)
        return render_template("dashboard.html", projects=[], error="Error loading project.")


@bp.route("/dashboard/projects/<int:project_id>", methods=["POST"])
@login_required
def edit(project_id: int):
    if not UserService.can_access_page(current_user, allowed_roles=[Role.User.value]):
        flash("You do not have permission to edit this project.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    db_session = get_db_session()
    project = db_session.query(Project).filter_by(id=project_id).first()
    if not project:
        abort(404)

    if project.user_id != current_user.id:
        abort(403)

    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    proj_type = request.form.get("type", "").strip()
    selected_venue = request.form.get("selected_venue", "").strip()
    selected_venue_url = request.form.get("selected_venue_url", "").strip()

    if not title or not description:
        flash("Title and description are required.", "danger")
        return redirect(url_for("project.view", project_id=project_id))

    project.title = title
    project.description = description
    project.type = proj_type or None  # Optional
    project.selected_venue = selected_venue or None  # Optional
    project.selected_venue_url = selected_venue_url or None  # Optional

    db_session.commit()
    flash("Project updated successfully.", "success")

    # Conditional redirect
    to_project: bool = request.args.get("to_project", "false").lower() == "true"
    if to_project:
        return redirect(url_for("project.view", project_id=project_id))
    else:
        return redirect(url_for("dashboard.dashboard"))


@bp.route("/dashboard/projects/<int:project_id>/delete", methods=["GET"])
@login_required
def delete(project_id: int):
    if not UserService.can_access_page(current_user, allowed_roles=[Role.User.value]):
        flash("You do not have permission to delete this project.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    db_session = get_db_session()
    project = db_session.query(Project).filter_by(id=project_id).first()
    if not project:
        flash("Project not found.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    if project.user_id != current_user.id:
        flash("You do not have permission to delete this project.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    try:
        db_session.delete(project)
        db_session.commit()
        flash("Project deleted successfully.", "success")
    except Exception as e:
        db_session.rollback()
        print("Error deleting project:", e)
        flash("Failed to delete project. Please try again.", "danger")

    return redirect(url_for("dashboard.dashboard"))
