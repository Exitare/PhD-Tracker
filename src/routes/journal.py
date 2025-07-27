from quart import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort
from quart_auth import current_user, login_required
from src.role import Role
from src.db.models import Project
from src.db import get_db_session
from typing import List
from src.models import AIJournalRecommendation
from src.services import UserService
from src.services.openai_service import OpenAIService
import logging
from src.services.log_service import AILogService

bp = Blueprint('journal', __name__)


@bp.route("/dashboard/projects/<int:project_id>/journal/recommendations", methods=["POST"])
@login_required
async def get_recommendations(project_id: int):
    if not UserService.can_access_page(current_user, allowed_roles=[Role.User.value]):
        await flash("You do not have permission to access this page.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    db_session = get_db_session()
    project = db_session.query(Project).filter_by(id=project_id).first()
    if not project:
        print("Project not found")
        return await render_template("dashboard.html", projects=[], error="Project not found.")

    if project.user_id != current_user.id:
        print("User does not have permission to access this project")
        return await render_template("dashboard.html", projects=[],
                               error="You do not have permission to access this project.")

    if not UserService.can_use_ai(current_user):
        await flash("Journal recommendations are only available for Plans that support AI.", "warning")
        return redirect(url_for("project.view", project_id=project_id))

    recommendations: List[AIJournalRecommendation]
    recommendations, usage = OpenAIService.generate_journal_recommendations(project_description=project.description)

    if not recommendations:
        await flash("No journal recommendations found for this project.", "info")
        return redirect(url_for("project.view", project_id=project_id))

    project.journal_recommendations = [r.to_json() for r in recommendations] or None

    token_count = usage.get("total_tokens", 0)
    logging.debug(f"AI token usage: {token_count}")

    AILogService.log_ai_usage(session=db_session, user_id=current_user.id, event_name="journal_recommendations",
                              used_tokens=token_count)

    # report usage
    UserService.report_ai_usage(user=current_user, token_count=token_count)

    db_session.commit()
    await flash("Journal recommendations updated successfully.", "success")

    return redirect(url_for("project.view", project_id=project_id))


@bp.route("/dashboard/projects/<int:project_id>/journal", methods=["POST"])
async def select(project_id: int):
    if not UserService.can_access_page(current_user, allowed_roles=[Role.User.value]):
        await flash("You do not have permission to access this page.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    db_session = get_db_session()
    project = db_session.query(Project).filter_by(id=project_id).first()
    if not project:
        abort(404)

    if project.user_id != current_user.id:
        abort(403)

    try:
        selected_journal = form.get("journal_name", "").strip()
        selected_journal_url = form.get("journal_link", "").strip()
        if not selected_journal:
            await flash("Please select a journal.", "danger")
            return redirect(url_for("project.view", project_id=project_id))

        project.selected_venue = selected_journal
        project.selected_venue_url = selected_journal_url
        db_session.commit()
        await flash("Journal selected successfully.", "success")
    except Exception as e:
        logging.error(f"Error selecting journal: {e}")
        db_session.rollback()
        await flash("Failed to delete project. Please try again.", "danger")

    return redirect(url_for("project.view", project_id=project_id))
