from datetime import datetime, timezone
from flask import Blueprint, request, redirect, render_template, url_for
from src.db.models import Project, SubProject
from src import db_session

bp = Blueprint('project', __name__)


@bp.route("/create-project", methods=["GET", "POST"])
def create_project():
    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]

        try:
            new_project = Project(title=title, description=description)
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
def view_project(project_id: int):
    try:
        # Load the project
        project = db_session.query(Project).filter_by(id=project_id).first()
        if not project:
            return render_template("dashboard.html", projects=[], error="Project not found.")

        # Load subprojects related to the project
        subprojects = db_session.query(SubProject).filter_by(project_id=project_id).all()

        return render_template(
            "project-detail.html",
            project=project,
            subprojects=subprojects
        )
    except Exception as e:
        print("Error loading project:", e)
        return render_template("dashboard.html", projects=[], error="Error loading project.")


@bp.route("/dashboard/projects/<int:project_id>", methods=["POST"])
def add_subproject(project_id: int):
    try:
        project = db_session.query(Project).filter_by(id=project_id).first()
        if not project:
            return render_template("dashboard.html", projects=[], error="Project not found.")

        title = request.form["title"]
        description = request.form["description"]

        new_subproject = SubProject(title=title, description=description, project_id=project_id,
                                    created_at=int(datetime.now(timezone.utc).timestamp() * 1000))
        db_session.add(new_subproject)
        db_session.commit()
        print("Added subproject:", title)

        return redirect(url_for("project.view_project", project_id=project_id))
    except Exception as e:
        db_session.rollback()
        print("Database error:", e)
        return render_template("project-detail.html", project_id=project_id,
                               error="Failed to add subproject. Please try again.")
