from flask import Blueprint, render_template, redirect, url_for, request, abort
from datetime import datetime, timezone
from src.db.models import SubProject, Milestone
from src import db_session

bp = Blueprint('subproject', __name__)


@bp.route("/dashboard/projects/<int:project_id>/subprojects/<int:subproject_id>")
def view(project_id: int, subproject_id: int):
    sub = db_session.query(SubProject).filter_by(id=subproject_id, project_id=project_id).first()
    if not sub:
        abort(404, description="Subproject not found")

    milestones = (
        db_session.query(
            Milestone.id,
            SubProject.title,
            Milestone.sub_project_id,
            Milestone.milestone,
            Milestone.due_date,
            Milestone.status,
            Milestone.notes
        )
        .filter(Milestone.sub_project_id == subproject_id)
        .join(SubProject, Milestone.sub_project_id == SubProject.id)
        .all()
    )

    return render_template(
        "sub-project-detail.html",
        project_title=sub.title,
        project_id=project_id,
        milestones=milestones
    )


@bp.route("/dashboard/projects/<int:project_id>/subprojects/<int:subproject_id>/edit", methods=["GET", "POST"])
def edit(project_id: int, subproject_id: int):
    sub = db_session.query(SubProject).filter_by(id=subproject_id).first()
    if not sub:
        abort(404, description="Subproject not found")

    if request.method == "POST":
        sub.title = request.form["title"]
        sub.description = request.form["description"]
        db_session.commit()
        return redirect(url_for("subproject.view", subproject_id=sub.id))

    return render_template("edit-subproject.html", subproject=sub)


@bp.route("/dashboard/projects/<int:project_id>/subprojects/<int:subproject_id>/delete", methods=["POST"])
def delete(project_id: int, subproject_id: int):
    sub = db_session.query(SubProject).filter_by(id=subproject_id).first()
    if not sub:
        abort(404, description="Subproject not found")

    project_id = sub.project_id
    db_session.delete(sub)
    db_session.commit()
    return redirect(url_for("project.view_project", project_id=project_id))
