from datetime import datetime, timezone
from flask import Blueprint, request, redirect, render_template, url_for
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
def view_project(project_id: int):
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
        # subprojects = db_session.query(SubProject).filter_by(project_id=project_id).all()

        return render_template(
            "project-detail.html",
            project=project,
            subprojects=subprojects
        )
    except Exception as e:
        print("Error loading project:", e)
        return render_template("dashboard.html", projects=[], error="Error loading project.")
