from datetime import datetime, timezone
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from src.db.models import User
from src.db import db_session
from flask_login import login_required, current_user, logout_user
from src.forms import EmailForm, PasswordForm, ThemeForm
from werkzeug.security import check_password_hash, generate_password_hash
import stripe
from src.services import JWTService, MailService, UserService
from sqlalchemy.exc import IntegrityError
from src.role import Role

bp = Blueprint("account", __name__)

ALLOWED_THEMES = {"lavender", "dark", "light", "solarized"}
EMAIL_REGEX = r"[^@]+@[^@]+\.[^@]+"


@bp.route("/account/panel", methods=["GET"])
@login_required
def panel():
    if not UserService.can_access_page(current_user, [Role.User.value]):
        flash("You do not have permission to access this page.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    try:
        user = db_session.query(User).filter_by(id=current_user.id).first()
        if not user:
            return redirect(url_for("auth.login"))

        email_form = EmailForm()
        password_form = PasswordForm()
        theme_form = ThemeForm()

        # Set the currently selected theme in the form
        current_theme = session.get('theme', 'lavender')
        theme_form.theme.data = current_theme

        return render_template(
            "account-panel/panel.html",
            email_form=email_form,
            password_form=password_form,
            theme_form=theme_form,
            user=current_user
        )
    except Exception as e:
        print("Error loading account:", e)
        logout_user()
        return redirect(url_for("auth.login"))


@bp.route("/account/email", methods=["POST"])
@login_required
def update_email():
    form = EmailForm(request.form)

    if form.validate():
        new_email = form.email.data.strip().lower()
        password = form.password.data

        if not check_password_hash(current_user.password_hash, password):
            flash("Incorrect password.", "danger")
            return redirect(url_for("account.panel"))

        if new_email == current_user.email:
            flash("New email must be different from your current email.", "warning")
            return redirect(url_for("account.panel"))

        if db_session.query(User).filter(User.email == new_email).first():
            flash("If the email is valid and available, you'll receive a verification link shortly.", "danger")
            return redirect(url_for("account.panel"))

        try:
            current_user.pending_email = new_email
            db_session.commit()
            MailService.send_verification_email(current_user)

            flash("If the email is valid and available, you'll receive a verification link shortly.", "success")
            return redirect(url_for("account.panel"))
        except IntegrityError:
            db_session.rollback()
            flash("Could not update email due to a database error.", "danger")
            return redirect(url_for("account.panel"))

    # If validation fails
    for field, errors in form.errors.items():
        for error in errors:
            flash(f"{getattr(form, field).label.text}: {error}", "danger")
    return redirect(url_for("account.panel"))


@bp.route("/account/password", methods=["POST"])
@login_required
def update_password():
    form = PasswordForm(request.form)

    if form.validate():
        # Check if the current password is correct
        if not check_password_hash(current_user.password_hash, form.current_password.data):
            flash("Current password is incorrect.", "danger")
            return redirect(url_for("account.panel"))

        # Prevent using the same password again
        if check_password_hash(current_user.password_hash, form.password.data):
            flash("New password cannot be the same as the current password.", "warning")
            return redirect(url_for("account.panel"))

        # Update password
        current_user.password_hash = generate_password_hash(form.password.data)
        db_session.commit()
        flash("Your password has been updated.", "success")
        # TODO: Send password change notification email

    else:
        # Show form validation errors
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{getattr(form, field).label.text}: {error}", "danger")

    return redirect(url_for("account.panel"))


@bp.route("/account/theme", methods=["POST"])
@login_required
def update_theme():
    selected_theme = request.form.get('theme')

    if selected_theme not in ALLOWED_THEMES:
        flash("Invalid theme selected.", "danger")
        return redirect(url_for('account.panel'))

    # Save theme to session (and optionally to DB for persistence)
    session['theme'] = selected_theme
    flash(f"Theme changed to '{selected_theme}'.", "success")

    return redirect(url_for('account.panel'))


@bp.route("/account/stripe", methods=["GET"])
@login_required
def manage_subscriptions():
    try:
        # open stripe customer portal
        if not current_user.stripe_customer_id:
            flash("You need to set up a Stripe customer ID first.", "warning")
            return redirect(url_for('account.panel'))

        stripe_customer_id = current_user.stripe_customer_id
        stripe_portal_session = stripe.billing_portal.Session.create(
            customer=stripe_customer_id,
            return_url=url_for('account.panel', _external=True)
        )
        return redirect(stripe_portal_session.url)
    except Exception as e:
        print(f"Stripe error: {e}")
        flash("An error occurred while managing subscriptions. Please try again.", "danger")
        return redirect(url_for('account.panel'))


@bp.route("/account/verify-email/<token>", methods=["GET"])
def verify_email(token):
    try:
        email = JWTService.verify_email_token(token)
        if not email:
            flash("Invalid or expired verification link.", "error")
            return redirect(url_for('auth.login'))

        user = db_session.query(User).filter_by(email=email).first()
        if not user:
            print("User not found for email:", email)
            flash("Token invalid.", "error")
            return redirect(url_for('auth.login'))

        if user.email_verified:
            print("Email already verified.")
            flash("Token invalid.", "info")
            return redirect(url_for('auth.login'))

        if user.pending_email == email:
            # Promote pending_email to main email
            user.email = user.pending_email
            user.pending_email = None

        user.email_verified = True
        user.email_verified_at = int(datetime.now(timezone.utc).timestamp() * 1000)
        db_session.commit()

        flash("Email successfully verified! You can now log in.", "success")
        return redirect(url_for('auth.login'))

    except Exception as e:
        print(f"Error verifying email: {e}")
        flash("An error occurred while verifying your email. Please try again.", "error")
        return redirect(url_for('auth.login'))


@bp.route("/account/code-refresh", methods=["POST"])
@login_required
def refresh_access_code():
    if not current_user or current_user.role != Role.Manager.value:
        flash("You do not have permission to perform this action.", "danger")
        return redirect(url_for('account.panel'))

    try:

        # Generate a new access code
        current_user.access_code = UserService.create_access_token()
        db_session.commit()

        flash("Access code refreshed successfully.", "success")
        return redirect(url_for('academia.panel'))

    except Exception as e:
        print(f"Error refreshing access code: {e}")
        flash("An error occurred while refreshing the access code. Please try again.", "danger")
        return redirect(url_for('academia.panel'))


@bp.route("/account/resend_activation_email", methods=["GET"])
@login_required
def resend_activation_email():
    if not current_user.email_verified:
        try:
            MailService.send_verification_email(current_user)
            flash("Activation email resent successfully. Please check your inbox.", "success")
        except Exception as e:
            print(f"Error sending activation email: {e}")
            flash("An error occurred while resending the activation email. Please try again.", "danger")
    else:
        flash("Your email is already verified.", "info")

    return redirect(url_for('academia.panel'))
