from datetime import datetime, timezone
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from src.db.models import User
from src.db import db_session
from flask_login import login_required, current_user, logout_user
from src.forms import EmailForm, PasswordForm, ThemeForm
import stripe

bp = Blueprint("account", __name__)

ALLOWED_THEMES = {"lavender", "dark", "light", "solarized"}


@bp.route("/account", methods=["GET"])
@login_required
def panel():
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
    pass


@bp.route("/account/password", methods=["POST"])
@login_required
def update_password():
    pass


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
