from datetime import datetime, timezone
from quart import Blueprint, render_template, request, redirect, url_for, flash, session
from src.db.models import User
from src.db import get_db_session
from quart_auth import login_required, current_user, logout_user
from src.forms import EmailForm, PasswordForm, ThemeForm
from werkzeug.security import check_password_hash, generate_password_hash
import stripe
from src.services import JWTService, MailService, UserService, TokenPayload
from sqlalchemy.exc import IntegrityError
from src.role import Role
from typing import Dict
from src.plans import Plans
import os
import logging

logger = logging.getLogger(__name__)

bp = Blueprint("account", __name__)

ALLOWED_THEMES: Dict[str, str] = {
    "lavender-dark": "Lavender (Dark)",
    "lavender-light": "Lavender (Light)",
    "solarized-light": "Solarized (Light)",
    "solarized-dark": "Solarized (Dark)",
}

EMAIL_REGEX = r"[^@]+@[^@]+\.[^@]+"



@bp.route("/account/panel", methods=["GET"])
@login_required
async def panel():


    args = await request.args    form = await request.form    if not UserService.can_access_page(current_user, [Role.User.value]):
        await flash("You do not have permission to access this page.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    db_session = get_db_session()
    try:
        user = db_session.query(User).filter_by(id=current_user.id).first()
        if not user:
            return redirect(url_for("auth.login"))

        email_form = EmailForm()
        password_form = PasswordForm()
        theme_form = ThemeForm()

        # Set the currently selected theme in the form
        current_theme = session.get('theme', 'lavender-dark')
        theme_form.theme.data = current_theme

        return await render_template(
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
async def update_email():


    args = await request.args    form = await request.form    form = EmailForm(request.form)

    if form.validate():
        new_email = form.email.data.strip().lower()
        password = form.password.data
        db_session = get_db_session()
        if not check_password_hash(current_user.password_hash, password):
            await flash("Incorrect password.", "danger")
            return redirect(url_for("account.panel"))

        if new_email == current_user.email:
            await flash("New email must be different from your current email.", "warning")
            return redirect(url_for("account.panel"))

        if db_session.query(User).filter(User.email == new_email).first():
            await flash("If the email is valid and available, you'll receive a verification link shortly.", "danger")
            return redirect(url_for("account.panel"))

        try:
            current_user.pending_email = new_email
            db_session.commit()
            MailService.send_verification_email(current_user)

            await flash("If the email is valid and available, you'll receive a verification link shortly.", "success")
            return redirect(url_for("account.panel"))
        except IntegrityError:
            db_session.rollback()
            await flash("Could not update email due to a database error.", "danger")
            return redirect(url_for("account.panel"))

    # If validation fails
    for field, errors in form.errors.items():
        for error in errors:
            await flash(f"{getattr(form, field).label.text}: {error}", "danger")
    return redirect(url_for("account.panel"))


@bp.route("/account/password", methods=["POST"])
@login_required
async def update_password():


    args = await request.args    form = await request.form    form = PasswordForm(request.form)

    if form.validate():
        db_session = get_db_session()
        # Check if the current password is correct
        if not check_password_hash(current_user.password_hash, form.current_password.data):
            await flash("Current password is incorrect.", "danger")
            return redirect(url_for("account.panel"))

        # Prevent using the same password again
        if check_password_hash(current_user.password_hash, form.password.data):
            await flash("New password cannot be the same as the current password.", "warning")
            return redirect(url_for("account.panel"))

        # Update password
        current_user.password_hash = generate_password_hash(form.password.data)
        db_session.commit()
        await flash("Your password has been updated.", "success")
        # TODO: Send password change notification email

    else:
        # Show form validation errors
        for field, errors in form.errors.items():
            for error in errors:
                await flash(f"{getattr(form, field).label.text}: {error}", "danger")

    return redirect(url_for("account.panel"))


@bp.route("/account/theme", methods=["POST"])
@login_required
async def update_theme():


    args = await request.args    form = await request.form    selected_theme = form.get('theme')

    if selected_theme not in ALLOWED_THEMES.keys():
        await flash("Invalid theme selected.", "danger")
        return redirect(url_for('account.panel'))

    # Save theme to session (and optionally to DB for persistence)
    session['theme'] = selected_theme
    await flash(f"Theme changed to '{ALLOWED_THEMES[selected_theme]}'.", "success")

    if current_user.role == Role.User.value:
        return redirect(url_for('account.panel'))
    elif current_user.role == Role.Manager.value:
        return redirect(url_for('academia.panel'))
    elif current_user.role == Role.Admin.value:
        return redirect(url_for('admin.panel'))


@bp.route("/account/stripe", methods=["GET"])
@login_required
async def manage_subscriptions():


    args = await request.args    form = await request.form    if current_user.managed_by:
        await flash("You cannot manage subscriptions for a managed account.", "warning")
        return redirect(url_for('account.panel'))

    try:
        # open stripe customer portal
        if not current_user.stripe_customer_id:
            await flash("You need to set up a Stripe customer ID first.", "warning")
            return redirect(url_for('account.panel'))

        stripe_customer_id = current_user.stripe_customer_id
        stripe_portal_session = stripe.billing_portal.Session.create(
            customer=stripe_customer_id,
            return_url=url_for('account.panel', _external=True)
        )
        return redirect(stripe_portal_session.url)
    except Exception as e:
        print(f"Stripe error: {e}")
        await flash("An error occurred while managing subscriptions. Please try again.", "danger")
        if current_user.role == Role.User.value:
            return redirect(url_for('account.panel'))
        elif current_user.role == Role.Manager.value:
            return redirect(url_for('academia.panel'))
        else:
            return redirect(url_for('admin.panel'))


@bp.route("/account/verify-email/<token>", methods=["GET"])
async def verify_email(token):


    args = await request.args    form = await request.form    try:
        payload: TokenPayload | None = JWTService.verify_token(token)

        if not payload or not payload.email:
            await flash("Invalid or expired verification link.", "error")
            return redirect(url_for('auth.login'))

        email = payload.email

        db_session = get_db_session()
        user = db_session.query(User).filter_by(email=email).first()
        if not user:
            print("User not found for email:", email)
            await flash("Token invalid.", "error")
            return redirect(url_for('auth.login'))

        if user.email_verified:
            print("Email already verified.")
            await flash("Token invalid.", "info")
            return redirect(url_for('auth.login'))

        if user.pending_email == email:
            # Promote pending_email to main email
            user.email = user.pending_email
            user.pending_email = None

        user.email_verified = True
        user.email_verified_at = int(datetime.now(timezone.utc).timestamp() * 1000)
        db_session.commit()

        await flash("Email successfully verified! You can now log in.", "success")
        return redirect(url_for('auth.login'))

    except Exception as e:
        print(f"Error verifying email: {e}")
        await flash("An error occurred while verifying your email. Please try again.", "error")
        return redirect(url_for('auth.login'))


@bp.route("/account/code-refresh", methods=["POST"])
@login_required
async def refresh_access_code():


    args = await request.args    form = await request.form    if not current_user or current_user.role != Role.Manager.value:
        await flash("You do not have permission to perform this action.", "danger")
        return redirect(url_for('account.panel'))

    db_session = get_db_session()
    try:

        # Generate a new access code
        current_user.access_code = UserService.create_access_token()
        db_session.commit()

        await flash("Access code refreshed successfully.", "success")
        return redirect(url_for('academia.panel'))

    except Exception as e:
        print(f"Error refreshing access code: {e}")
        await flash("An error occurred while refreshing the access code. Please try again.", "danger")
        return redirect(url_for('academia.panel'))


@bp.route("/account/resend_activation_email", methods=["GET"])
@login_required
async def resend_activation_email():


    args = await request.args    form = await request.form    if not current_user.email_verified:
        try:
            MailService.send_verification_email(current_user)
            current_user.activation_email_triggered_at = int(datetime.now(timezone.utc).timestamp() * 1000)
            db_session = get_db_session()
            db_session.commit()
            await flash("Activation email resent successfully. Please check your inbox.", "success")
        except Exception as e:
            print(f"Error sending activation email: {e}")
            await flash("An error occurred while resending the activation email. Please try again.", "danger")
    else:
        await flash("Your email is already verified.", "info")

    return redirect(request.referrer or url_for('dashboard.dashboard'))


@bp.route("/account/choose-plan", methods=["POST"])
@login_required
async def choose_plan():


    args = await request.args    form = await request.form    plan: str = form.get('plan')
    user: User = current_user

    if not user or not UserService.can_access_page(user, [Role.User.value]):
        await flash("You do not have permission to access this page.", "danger")
        return redirect(url_for('dashboard.dashboard'))

    if plan not in [Plans.Student.value, Plans.StudentPlus.value, Plans.StudentPro.value]:
        await flash("Please select a valid plan option.", "warning")
        return redirect(url_for('account.panel'))

    db_session = get_db_session()
    try:
        # Downgrading to Student (free) plan
        if plan == Plans.Student.value:
            if user.stripe_subscription_id:
                # Set subscription to cancel at end of current billing period
                subscription = stripe.Subscription.modify(
                    user.stripe_subscription_id,
                    cancel_at_period_end=True
                )

                price_ids = [item["price"]["id"] for item in subscription["items"]["data"]]
                current_user.stripe_subscription_id = subscription["id"]
                current_user.plan = Plans.get_plan_name(price_ids)
                current_user.stripe_subscription_item_ids = ",".join(price_ids)
                current_user.stripe_subscription_expires_at = int(
                    subscription["items"].data[0]["current_period_end"] * 1000)
                current_user.stripe_subscription_canceled = bool(subscription["cancel_at_period_end"])
                db_session.commit()

            await flash(
                "Your subscription will be cancelled at the end of the current period and downgraded to the free Student plan.",
                "success")
            return redirect(url_for("account.panel"))

        # Upgrading to Student+ or Student Pro
        if plan == Plans.StudentPlus.value:
            logger.debug(f"Gathering price for plan: {plan}")
            price_items = [
                {"price": os.environ["STUDENT_PLUS_PRICE_ID"]}
            ]
        else:
            logger.debug(f"Gathering prices for plan: {plan}")
            price_items = [
                {"price": os.environ["STUDENT_PRO_OVERCHARGE_PRICE_ID"]},  # metered
                {"price": os.environ["STUDENT_PRO_PRICE_ID"], "quantity": 1}  # licensed
            ]

        if user.stripe_subscription_id:
            subscription = stripe.Subscription.retrieve(user.stripe_subscription_id)
            current_items = subscription["items"]["data"]
            items_to_delete = [{"id": item["id"], "deleted": True} for item in current_items]

            updated = stripe.Subscription.modify(
                user.stripe_subscription_id,
                cancel_at_period_end=False,
                proration_behavior='create_prorations',
                items=items_to_delete + price_items
            )

            subscription_item_ids = [item["id"] for item in updated["items"]["data"]]

            user.plan = plan
            user.stripe_subscription_id = updated["id"]
            user.stripe_subscription_item_ids = ",".join(subscription_item_ids)
            user.stripe_subscription_canceled = updated["cancel_at_period_end"]
            logger.debug(f"Canceled at period end: {user.stripe_subscription_canceled}")

            if int(updated["items"].data[0]["current_period_end"] * 1000):
                user.stripe_subscription_expires_at = int(updated["items"].data[0]["current_period_end"] * 1000)
            db_session.commit()

            await flash("Your subscription was successfully updated.", "success")
            return redirect(url_for("account.panel"))

        elif user.stripe_customer_id:
            checkout_session = stripe.checkout.Session.create(
                customer=user.stripe_customer_id,
                payment_method_types=['card'],
                line_items=price_items,
                mode='subscription',
                success_url=url_for('account.stripe_success', _external=True) + "?session_id={CHECKOUT_SESSION_ID}",
                cancel_url=url_for('account.panel', _external=True),
            )
            return redirect(checkout_session.url)

        else:
            await flash("Stripe customer not found for this account.", "danger")
            return redirect(url_for("account.panel"))

    except Exception as e:
        logger.exception("Stripe subscription error")
        await flash("An error occurred while processing your subscription. Please try again.", "danger")
        return redirect(url_for("account.panel"))


@bp.route("/account/stripe/success", methods=["GET"])
@login_required
async def stripe_success():


    args = await request.args    form = await request.form    session_id = args.get("session_id")
    if not session_id:
        await flash("No session ID provided.", "danger")
        return redirect(url_for("account.panel"))

    db_session = get_db_session()
    try:
        session = stripe.checkout.Session.retrieve(session_id)

        # if not paid or not completed
        if session["payment_status"] != "paid" or session["status"] != "complete":
            await flash("Payment was not successful. Please try again.", "danger")
            return redirect(url_for("account.panel"))

        subscription_id = session.get("subscription")
        if not subscription_id:
            await flash("No subscription found in the session.", "danger")
            return redirect(url_for('account.panel'))

        subscription = stripe.Subscription.retrieve(subscription_id)
        try:
            stripe.Subscription.modify(
                subscription["id"],
                billing_thresholds={
                    "amount_gte": 2500  # $25 in cents
                }
            )
        except Exception as e:
            print("Stripe billing threshold error:", e)
            print("Subscription details:", subscription)

        # Get the first subscription item (usually one per sub)
        try:
            if subscription["items"]["data"]:
                # get prices ids from subscription items
                price_ids = [item["price"]["id"] for item in subscription["items"]["data"]]
                current_user.stripe_subscription_id = subscription_id
                current_user.plan = Plans.get_plan_name(price_ids)
                current_user.stripe_subscription_item_ids = ",".join(price_ids)
                current_user.stripe_subscription_expires_at = int(
                    subscription["items"].data[0]["current_period_end"] * 1000)
                current_user.stripe_subscription_canceled = bool(subscription["cancel_at_period_end"])
                db_session.commit()
                await flash(f"Your {current_user.plan} subscription is now active!", "success")
            else:
                await flash("No subscription items found. Contact support.", "danger")

        except Exception as e:
            logger.exception("Error processing subscription items")
            await flash("An error occurred while processing your subscription. Please try again.", "danger")

    except Exception as e:
        logger.exception("Error retrieving Stripe session")
        await flash("An error occurred while processing your payment. Please try again.", "danger")

    return redirect(url_for("account.panel"))
