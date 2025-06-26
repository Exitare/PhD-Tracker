from flask import Blueprint, render_template, redirect, url_for, request, abort
from datetime import datetime, timezone
from src.db.models import SubProject, Milestone, Project
from src import db_session
from src.openai_client import generate_milestones

bp = Blueprint('subproject', __name__)


@bp.route("/dashboard/projects/<int:project_id>/subprojects", methods=["POST"])
def create(project_id: int):
    try:
        project = db_session.query(Project).filter_by(id=project_id).first()
        if not project:
            return render_template("dashboard.html", projects=[], error="Project not found.")

        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        ai_option = request.form.get("ai_option", "")
        deadline = request.form.get("deadline", "").strip()

        if not title or not description or not ai_option or not deadline:
            return render_template("project-detail.html", project_id=project_id, project=project,
                                   error="All fields are required, including deadline and AI selection.")

        new_subproject = SubProject(
            title=title,
            description=description,
            project_id=project_id,
            created_at=int(datetime.now(timezone.utc).timestamp() * 1000)
        )
        db_session.add(new_subproject)
        db_session.flush()  # Needed to get new_subproject.id before commit

        # If AI is requested, generate and add milestones
        if ai_option:
            print("Generating milestones using AI...")
            ai_milestones = generate_milestones(title, deadline)
            for ai_m in ai_milestones:
                db_milestone = Milestone(
                    sub_project_id=new_subproject.id,
                    milestone=ai_m.milestone,
                    due_date=ai_m.due_date,
                )
                db_session.add(db_milestone)
            print(f"{len(ai_milestones)} AI milestones created.")

        db_session.commit()
        return redirect(url_for("project.view_project", project_id=project_id))

    except Exception as e:
        db_session.rollback()
        print("Database error:", e)
        return render_template("project-detail.html", project_id=project_id,
                               error="Failed to add subproject. Please try again.")


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
