from datetime import datetime, timezone
from flask import Blueprint, request, redirect, render_template, url_for, abort, flash
from src.db.models import Project, SubProject, Milestone
from src import db_session
from flask_login import current_user, login_required
import stripe
from typing import List
from src.models import AIJournalRecommendation
from src.openai_client import OpenAIService
import logging

from src.plans import Plans
from src.services.log_service import AILogService

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
def edit(project_id: int):
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


@bp.route("/dashboard/projects/<int:project_id>/journal_recommendations", methods=["POST"])
@login_required
def get_journal_recommendations(project_id: int):
    project = db_session.query(Project).filter_by(id=project_id).first()
    if not project:
        return render_template("dashboard.html", projects=[], error="Project not found.")

    if project.user_id != current_user.id:
        return render_template("dashboard.html", projects=[],
                               error="You do not have permission to access this project.")

    if current_user.plan != Plans.StudentPlus.value:
        flash("Journal recommendations are only available for Student+ plan users.", "warning")
        return redirect(url_for("project.view", project_id=project_id))

    recommendations: List[AIJournalRecommendation]
    recommendations, usage = OpenAIService.generate_journal_recommendations(project_description=project.description)

    if not recommendations:
        flash("No journal recommendations found for this project.", "info")
        return redirect(url_for("project.view", project_id=project_id))

    project.venue_recommendations = [r.to_json() for r in recommendations] or None

    token_count = usage.get("total_tokens", 0)
    logging.debug(f"AI token usage: {token_count}")

    AILogService.log_ai_usage(session=db_session, user_id=current_user.id, event_name="journal_recommendations",
                              used_tokens=token_count)

    # report usage
    stripe.billing.MeterEvent.create(
        event_name="tokenrequests",
        payload={
            "value": str(token_count),
            "stripe_customer_id": current_user.stripe_customer_id,
        }
    )

    db_session.commit()
    flash("Journal recommendations updated successfully.", "success")

    return redirect(url_for("project.view", project_id=project_id))


@bp.route("/dashboard/projects/<int:project_id>/select_journal", methods=["POST"])
def select_journal(project_id: int):
    project = db_session.query(Project).filter_by(id=project_id).first()
    if not project:
        abort(404)

    if project.user_id != current_user.id:
        abort(403)

    try:
        selected_journal = request.form.get("journal_name", "").strip()
        selected_journal_url = request.form.get("journal_link", "").strip()
        if not selected_journal:
            flash("Please select a journal.", "danger")
            return redirect(url_for("project.view", project_id=project_id))

        project.selected_venue = selected_journal
        project.selected_venue_url = selected_journal_url
        db_session.commit()
        flash("Journal selected successfully.", "success")
    except Exception as e:
        db_session.rollback()
        flash("Failed to delete project. Please try again.", "danger")

    return redirect(url_for("project.view", project_id=project_id))
