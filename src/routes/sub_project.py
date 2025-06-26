from flask import Blueprint, render_template, redirect, url_for, request, abort
from datetime import datetime, timezone
from src.db.models import SubProject, Milestone, Project
from src import db_session

bp = Blueprint('subproject', __name__)


@bp.route("/dashboard/projects/<int:project_id>/subprojects/<int:subproject_id>")
def view(project_id: int, subproject_id: int):
    sub = db_session.query(SubProject).filter_by(id=subproject_id, project_id=project_id).first()
    if not sub:
        abort(404, description="Subproject not found")

    milestones = (
        db_session.query(Milestone)
        .filter_by(sub_project_id=subproject_id)
        .all()
    )

    project = db_session.query(Project).filter_by(id=project_id).first()
    if not project:
        abort(404, description="Project not found")

    return render_template(
        "sub-project-detail.html",
        project=project,
        subproject=sub,
        milestones=milestones
    )


@bp.route("/dashboard/projects/<int:project_id>/subprojects/<int:subproject_id>", methods=["POST"])
def edit(project_id: int, subproject_id: int):
    sub = db_session.query(SubProject).filter_by(id=subproject_id, project_id=project_id).first()
    if not sub:
        abort(404)

    sub.title = request.form.get("title", sub.title)
    sub.description = request.form.get("description", sub.description)

    try:
        db_session.commit()
    except Exception as e:
        db_session.rollback()
        print("Error editing subproject:", e)

    return redirect(url_for("project.view_project", project_id=project_id))


@bp.route("/dashboard/projects/<int:project_id>/subprojects/<int:subproject_id>/delete", methods=["POST"])
def delete(project_id: int, subproject_id: int):
    sub = db_session.query(SubProject).filter_by(id=subproject_id).first()
    if not sub:
        abort(404, description="Subproject not found")

    project_id = sub.project_id
    db_session.delete(sub)
    db_session.commit()
    return redirect(url_for("project.view_project", project_id=project_id))
