from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import current_user, login_required
from src.db.models import Project, User
from src import db_session
import threading
import json
import stripe
from typing import List
from src.handler.OpenAIHandler import OpenAIHandler
from src.models import AIJournalRecommendation
from src.services.openai_service import OpenAIService
import logging
from src.plans import Plans, StripeMeter
from src.services.log_service import AILogService

bp = Blueprint('journal', __name__)

llm_data = []


@bp.route("/dashboard/projects/<int:project_id>/journal/recommendations", methods=["POST"])
@login_required
def get_recommendations(project_id: int):
    project = db_session.query(Project).filter_by(id=project_id).first()
    if not project:
        print("Project not found")
        return render_template("dashboard.html", projects=[], error="Project not found.")

    if project.user_id != current_user.id:
        print("User does not have permission to access this project")
        return render_template("dashboard.html", projects=[],
                               error="You do not have permission to access this project.")

    if current_user.plan == Plans.Student.value:
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
        event_name=StripeMeter.TokenRequests.value,
        payload={
            "value": str(token_count),
            "stripe_customer_id": current_user.stripe_customer_id,
        }
    )

    db_session.commit()
    flash("Journal recommendations updated successfully.", "success")

    return redirect(url_for("project.view", project_id=project_id))


@bp.route("/dashboard/projects/<int:project_id>/journal", methods=["POST"])
def select(project_id: int):
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


@bp.route("/dashboard/projects/<int:project_id>/journal/<string:journal_name>/requirements/generate")
def start_venue_requirements_job(project_id: int, journal_name: str):
    project: Project = db_session.query(Project).filter_by(id=project_id).first()
    if not project:
        return render_template("dashboard.dashboard", projects=[])
    if project.user_id != current_user.id:
        return render_template("dashboard.dashboard", projects=[])

    thread = threading.Thread(target=OpenAIHandler.get_journal_requirements,
                              args=(db_session, project.id, journal_name, current_user.id,))
    thread.start()
    return jsonify({"status": "Task started", "journal": journal_name})


@bp.route("/dashboard/projects/<int:project_id>/journal/<string:journal_name>/requirements/result")
def get_venue_requirements_result(project_id: int, journal_name: str):
    # Load project from DB that belongs to current user
    project = db_session.query(Project).filter_by(id=project_id, user_id=current_user.id).first()

    if project and project.venue_requirements:
        flash("Requirements have been retrieved.", "success")
        return jsonify({"status": "ready"})

    return jsonify({"status": "Processing or not found"}), 202


@bp.route("/dashboard/projects/<int:project_id>/journal/<string:journal_name>/requirements")
def view(project_id: int, journal_name: str):
    project: Project = db_session.query(Project).filter_by(id=project_id, user_id=current_user.id).first()

    if not project:
        flash("Project not found or you do not have permission to access it.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    if not project.venue_requirements:
        flash("Venue requirements not available. Please generate them first.", "warning")
        return redirect(
            url_for("journal.start_venue_requirements_job", project_id=project_id, journal_name=journal_name))

    try:
        project.venue_requirements = json.loads(project.venue_requirements)
        project.venue_requirements = project.venue_requirements[0]
    except json.JSONDecodeError:
        flash("Failed to decode venue requirements. Please try generating them again.", "danger")
        return redirect(
            url_for("project.view", project_id=project_id, journal_name=journal_name))

    return render_template('journal/requirements.html', project_id=project_id, journal_name=journal_name,
                           project=project)
