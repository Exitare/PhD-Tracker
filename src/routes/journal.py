from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import current_user, login_required
from openai import project

from src.db.models import Project, User
from src import db_session
import threading
import time
import stripe
from typing import List
from src.models import AIJournalRecommendation
from src.openai_client import OpenAIService
import logging
from src.plans import Plans
from src.services.log_service import AILogService

bp = Blueprint('journal', __name__)

llm_data = []


@bp.route("/dashboard/projects/<int:project_id>/journal/recommendations", methods=["POST"])
@login_required
def get_recommendations(project_id: int):
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


@bp.route("/dashboard/projects/<int:project_id>/journal/<string:journal_name>/requirements")
def start_requirements_job(project_id: int, journal_name: str):
    project: Project = db_session.query(Project).filter_by(id=project_id).first()
    if not project:
        return render_template("dashboard.dashboard", projects=[])
    if project.user_id != current_user.id:
        return render_template("dashboard.dashboard", projects=[])

    thread = threading.Thread(target=call_llm_and_store, args=(journal_name, project, current_user.id,))
    thread.start()
    return jsonify({"status": "Task started", "journal": journal_name})


@bp.route("/dashboard/projects/<int:project_id>/journal/<string:journal_name>/requirements/result")
def get_requirements_result(project_id: int, journal_name: str):
    global llm_data
    result = llm_data
    if result:
        flash("LLM requirements fetched successfully.", "success")
        return jsonify(result)
    return jsonify({"status": "Processing or not found"}), 202


def call_llm_and_store(journal_name: str, project: Project, user_id: int):
    print(f"Calling LLM for: {journal_name}")
    time.sleep(5)
    print(f"Completed LLM for: {journal_name}")

    result = {"journal": journal_name, "guidelines": "... extracted json ..."}
    global llm_data
    llm_data = result
    print(f"LLM data stored: {result}")

    # Re-fetch user in this thread
    user = db_session.get(User, user_id)
    if user:
        project.venue_requirements = "This is my requirement"
        db_session.add(project)
        db_session.commit()
        print("✅ Result committed to user record.")
    else:
        print("❌ User not found.")
