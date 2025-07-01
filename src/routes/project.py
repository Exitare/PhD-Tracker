from datetime import datetime, timezone
from flask import Blueprint, request, redirect, render_template, url_for, abort, flash
from src.db.models import Project, SubProject, Milestone
from src import db_session
from flask_login import current_user, login_required

bp = Blueprint('project', __name__)


@bp.route("/create-project", methods=["GET", "POST"])
@login_required
def create_project():
    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]

        try:
            new_project: Project = Project(title=title,
                                           description=description,
                                           created_at=int(datetime.now(timezone.utc).timestamp() * 1000),
                                           user_id=current_user.id)
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
    try:
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

        for item in subprojects:
            sub = item["subproject"]
            sub.deadline_dt = datetime.fromtimestamp(sub.deadline / 1000, tz=timezone.utc)

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
def edit(project_id):
    project = db_session.query(Project).filter_by(id=project_id).first()
    if not project:
        abort(404)

    if project.user_id != current_user.id:
        abort(403)

    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()

    if not title or not description:
        flash("Title and description are required.", "danger")
        return redirect(url_for("project.view", project_id=project_id))

    project.title = title
    project.description = description
    db_session.commit()

    flash("Project updated successfully.", "success")
    return redirect(url_for("dashboard.dashboard", project_id=project_id))
