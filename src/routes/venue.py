import os
from src.handler.RAG import RAGHandler
from quart import Blueprint, render_template, jsonify, flash, redirect, url_for
import threading
from quart_auth import current_user, login_required
from src.db.models import Project
from src.db import get_db_session
from src.handler.OpenAIHandler import OpenAIHandler
from quart import request
import json
from src.plans import Plans
from src.services import UserService
from src.role import Role
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('venue', __name__)
use_rag: bool = bool(int(os.environ.get('USE_RAG')))


@bp.route("/dashboard/projects/<int:project_id>/venue/<string:venue_name>/requirements/regenerate")
@login_required
async def regenerate_requirements(project_id: int, venue_name: str):
    if not UserService.can_access_page(current_user, allowed_roles=[Role.User.value]):
        await flash("You do not have permission to view this page.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    db_session = get_db_session()
    project: Project = db_session.query(Project).filter_by(id=project_id).first()

    if not project or project.user_id != current_user.id:
        await flash("Project not found or access denied.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    if current_user.plan == Plans.Student.value:
        await flash("You need a paid plan to regenerate venue requirements.", "warning")
        return redirect(url_for("venue.view", project_id=project_id, venue_name=venue_name))

    if project.type != 'paper' and project.type != 'poster':
        await flash("Unsupported project type for venue requirements.", "danger")
        return redirect(url_for("project.view", project_id=project_id))

    if use_rag and current_user.plan == Plans.StudentPro.value:
        logger.info("🔄 Regenerating venue requirements using RAG...")
        success = RAGHandler.extract_venue_requirements(project_id=project_id, user_id=current_user.id,
                                                        venue_name=venue_name)

    else:
        logger.info("🔄 Regenerating venue requirements using OpenAI...")
        success = OpenAIHandler.get_venue_requirements(db_session=db_session, project=project, venue_name=venue_name,
                                                       user_id=current_user.id)

    # reload project to get updated requirements
    project = db_session.query(Project).filter_by(id=project_id, user_id=current_user.id).first()
    if not project:
        await flash("Project not found or you do not have permission to access it.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    if not project.venue_requirements:
        await flash("Venue requirements not available. Please generate them first.", "warning")
        return redirect(url_for("project.view", project_id=project_id))

    try:
        project.venue_requirements = json.loads(project.venue_requirements)
    except json.JSONDecodeError:
        await flash("Failed to decode venue requirements. Please try generating them again.", "danger")
        return redirect(
            url_for("project.view", project_id=project_id))

    if success:
        await flash("Venue requirements regenerated successfully.", "success")

    return await render_template(
        f"{'journal' if project.type == 'paper' else project.type}/requirements.html",
        project_id=project_id,
        journal_name=venue_name,
        project=project
    )


@bp.route("/dashboard/projects/<int:project_id>/venue/<string:venue_name>/requirements/generate")
@login_required
async def start_venue_requirements_job(project_id: int, venue_name: str):
    if not UserService.can_access_page(current_user, allowed_roles=[Role.User.value]):
        await flash("You do not have permission to view this page.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    db_session = get_db_session()
    project: Project = db_session.query(Project).filter_by(id=project_id).first()
    if not project:
        return await render_template("dashboard.dashboard", projects=[])
    if project.user_id != current_user.id:
        return await render_template("dashboard.dashboard", projects=[])

    if project.type != 'paper' and project.type != 'poster':
        await flash("Unsupported project type for venue requirements.", "danger")
        return redirect(url_for("project.view", project_id=project_id))

    if use_rag and current_user.plan == Plans.StudentPro.value:
        logger.info("Using RAG to extract venue requirements...")
        thread = threading.Thread(target=RAGHandler.extract_venue_requirements,
                                  args=(project_id, current_user.id, venue_name,))

    else:
        logger.info("Using OpenAI to get venue requirements...")
        thread = threading.Thread(target=OpenAIHandler.get_venue_requirements,
                                  args=(db_session, project, venue_name, current_user.id,))

    thread.start()
    return jsonify({"status": "Task started", "venue": venue_name})


@bp.route("/dashboard/projects/<int:project_id>/venue/<string:venue_name>/requirements/result")
@login_required
async def get_venue_requirements_result(project_id: int, venue_name: str):
    if not UserService.can_access_page(current_user, allowed_roles=[Role.User.value]):
        await flash("You do not have permission to view this page.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    db_session = get_db_session()
    # Load project from DB that belongs to current user
    project: Project = db_session.query(Project).filter_by(id=project_id, user_id=current_user.id).first()
    if project and project.venue_requirements:
        await flash("Requirements have been retrieved.", "success")
        return jsonify({"status": "ready"})

    return jsonify({"status": "Processing or not found"}), 202


@bp.route("/dashboard/projects/<int:project_id>/venue/<string:venue_name>/requirements")
@login_required
async def view(project_id: int, venue_name: str):
    if not UserService.can_access_page(current_user, allowed_roles=[Role.User.value]):
        await flash("You do not have permission to view this page.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    db_session = get_db_session()
    project: Project = db_session.query(Project).filter_by(id=project_id, user_id=current_user.id).first()

    if not project:
        await flash("Project not found or you do not have permission to access it.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    if not project.venue_requirements:
        await flash("Venue requirements not available. Please generate them first.", "warning")
        return redirect(
            url_for("project.view", project_id=project_id))

    try:
        project.venue_requirements = json.loads(project.venue_requirements)
    except json.JSONDecodeError:
        await flash("Failed to decode venue requirements. Please try generating them again.", "danger")
        return redirect(
            url_for("project.view", project_id=project_id))

    if project.type == 'paper':
        return await render_template('journal/requirements.html', project_id=project_id, journal_name=venue_name,
                               project=project)
    elif project.type == 'poster':
        return await render_template('poster/requirements.html', project_id=project_id, journal_name=venue_name,
                               project=project)

    else:
        await flash("Unsupported project type for venue requirements.", "danger")
        return redirect(url_for("project.view", project_id=project_id))


@bp.route("/dashboard/projects/<int:project_id>/venue/<string:venue_name>/requirements/save", methods=["POST"])
@login_required
async def save_requirements(project_id: int, venue_name: str):
    if not UserService.can_access_page(current_user, allowed_roles=[Role.User.value]):
        await flash("You do not have permission to view this page.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    db_session = get_db_session()
    project: Project = db_session.query(Project).filter_by(id=project_id, user_id=current_user.id).first()

    if not project:
        await flash("Project not found or you do not have permission to access it.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    if project.type == 'poster':
        try:
            updated_requirements = {
                "abstract_submission_due": form.get("abstract_submission_due", "").strip(),
                "final_submission_due": form.get("final_submission_due", "").strip(),
                "poster_networking_hours": form.get("poster_networking_hours", "").strip(),
                "source_url": form.get("source_url", "").strip(),
            }

            if not any(updated_requirements.values()):
                await flash("At least one requirement must be provided.", "danger")
                return redirect(url_for("poster.view", project_id=project_id, journal_name=venue_name))

            project.venue_requirements_data = updated_requirements
            db_session.commit()
            await flash("Venue requirements saved successfully.", "success")
        except Exception as e:
            logger.exception(f"Error saving venue requirements.")
            logger.exception(e)
            db_session.rollback()
            await flash(f"Failed to save venue requirements: {str(e)}", "danger")

    elif project.type == 'paper':
        pass

    return redirect(url_for("venue.view", project_id=project_id, venue_name=venue_name))
