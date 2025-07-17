from datetime import datetime, timezone, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from src.db.models import User
from src.db import get_db_session
from flask_login import login_required, current_user
import stripe
import os
from src.plans import Plans
from src.services import MailService, JWTService, TokenPayload
from src.role import Role
import jwt
import logging
from src.services.discord_service import DiscordService

logger = logging.getLogger(__name__)

bp = Blueprint("auth", __name__)


@bp.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    if request.method == "GET":
        token = request.args.get("token")
        if not token:
            flash("Missing token.", "error")
            return redirect(url_for('auth.login'))

        print(token)
        token_payload = JWTService.verify_token(token)
        if not token_payload:
            flash("Invalid or expired password reset link.", "error")
            return redirect(url_for('auth.login'))

        return render_template("auth/reset_password.html", token=token)

    elif request.method == "POST":
        # POST request
        token = request.form.get("token")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if not token:
            flash("Missing token.", "error")
            return redirect(url_for('auth.login'))

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("auth/reset_password.html", token=token)

        token_payload: TokenPayload = JWTService.verify_token(token)
        if not token_payload:
            flash("Invalid or expired password reset link.", "error")
            return redirect(url_for('auth.login'))

        try:
            user_id = token_payload.id
            db_session = get_db_session()
            user = db_session.query(User).filter_by(id=user_id).first()

            if not user:
                logger.debug(f"User not found: {user_id}")
                flash("The token provided is invalid.", "error")
                return redirect(url_for('auth.login'))

            user.password_hash = generate_password_hash(password)
            db_session.commit()

            flash("Password successfully reset. You can now log in.", "success")
            return redirect(url_for('auth.login'))

        except Exception as e:
            logger.error(f"Error resetting password: {e}")
            flash("An error occurred while resetting your password. Please try again.", "error")
            return render_template("auth/reset_password.html", token=token)


@bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        db_session = get_db_session()
        user = db_session.query(User).filter_by(email=email).first()

        if not user:
            flash("If an account with that email exists, a reset link has been sent.", "info")
            return redirect(url_for("auth.login"))

        MailService.send_password_reset_email(user=user)
        flash("If an account with that email exists, a reset link has been sent.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/forgot_password.html")


# Register
@bp.route('/register', methods=['GET', 'POST'])
def register_step1():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        access_code = request.form.get('access_code')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')

        # Input validation
        if not email or not password:
            error = "Email and password are required."
            return render_template('auth/register_step1.html', error=error, email=email)

        # TODO: Add email validation regex
        # TODO: Add password strength validation
        # Check if user already exists
        db_session = get_db_session()
        existing_user = db_session.query(User).filter_by(email=email).first()
        if existing_user:
            error = "If the email is valid and available, you'll receive a verification link shortly."
            return render_template('auth/register_step1.html', error=error, email=email)

        managing_user = None
        if access_code:
            if not first_name or not last_name:
                error = "First name and last name are required when using an access code."
                return render_template('auth/register_step1.html', error=error, email=email)

            # select the user with the access code
            managing_user = db_session.query(User).filter_by(access_code=access_code).first()
            if not managing_user or managing_user.plan == Plans.Student.value:
                error = "Invalid access code. Please check and try again."
                return render_template('auth/register_step1.html', error=error, email=email)

            # extract the email domain from the manager's email
            manager_email_domain = managing_user.email.split('@')[-1]
            # check if the email domain matches the manager's email domain
            if email.split('@')[-1] != manager_email_domain:
                error = f"Email domain must match the organizations domain: {manager_email_domain}"
                return render_template('auth/register_step1.html', error=error, email=email)

        try:
            # Create Stripe customer first
            stripe_customer = stripe.Customer.create(email=email)

            # Then create user and assign stripe_customer_id
            if access_code and managing_user:
                user = User(
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    password_hash=generate_password_hash(password),
                    stripe_customer_id=stripe_customer.id,
                    created_at=int(datetime.now(timezone.utc).timestamp() * 1000),
                    organization_name=managing_user.organization_name,
                    managed_by=managing_user.id,
                    managed_by_stripe_id=managing_user.stripe_id,
                )

            else:
                user = User(
                    email=email,
                    password_hash=generate_password_hash(password),
                    stripe_customer_id=stripe_customer.id,
                    created_at=int(datetime.now(timezone.utc).timestamp() * 1000)
                )
            db_session.add(user)
            db_session.commit()

            # send verification email
            MailService.send_verification_email(user)
            DiscordService.send_message(f"A new user has registered: {user.email} (ID: {user.id})")

            login_user(user)
            if not access_code:
                return redirect(url_for('auth.choose_plan'))
            else:
                return redirect(url_for('auth.introduction'))

        except Exception as e:
            db_session.rollback()
            print(f"Registration error: {e}")
            error = "An error occurred during registration. Please try again."
            return render_template('auth/register_step1.html', error=error, email=email)

    return render_template('auth/register_step1.html')


@bp.route('/choose-plan', methods=['GET', 'POST'])
@login_required
def choose_plan():
    if request.method == 'POST':
        if current_user.plan != Plans.Student.value:
            flash("You have already selected a plan. Please contact support if you need to change it.", "warning")
            return redirect(url_for('auth.introduction'))

        db_session = get_db_session()
        plan: str = request.form.get('plan')

        if plan == Plans.StudentPlus.value:
            if not current_user.stripe_customer_id:
                flash("Stripe customer not found for this account.", "danger")
                return redirect(url_for('auth.choose_plan'))

            try:
                checkout_session = stripe.checkout.Session.create(
                    customer=current_user.stripe_customer_id,
                    payment_method_types=['card'],
                    line_items=[{
                        'price': os.environ.get("STUDENT_PLUS_PRICE_ID"),
                    }],
                    mode='subscription',  # change to 'payment' if it's a one-time purchase
                    success_url=url_for('auth.stripe_success', _external=True) + "?session_id={CHECKOUT_SESSION_ID}",
                    cancel_url=url_for('auth.choose_plan', _external=True),
                )
                return redirect(checkout_session.url)
            except Exception as e:
                print(f"Stripe error: {e}")
                flash("An error occurred while creating the Stripe checkout session. Please try again.", "danger")

                return redirect(url_for('auth.choose_plan'))

        elif plan == Plans.StudentPro.value:
            print("Student Pro plan selected")
            if not current_user.stripe_customer_id:
                flash("Stripe customer not found for this account.", "danger")
                return redirect(url_for('auth.choose_plan'))

            try:
                checkout_session = stripe.checkout.Session.create(
                    customer=current_user.stripe_customer_id,
                    payment_method_types=['card'],
                    line_items=[
                        {
                            'price': os.environ.get("STUDENT_PRO_OVERCHARGE_PRICE_ID"),
                        },
                        {
                            'price': os.environ.get("STUDENT_PRO_PRICE_ID"),
                            'quantity': 1
                        }
                    ],
                    mode='subscription',  # change to 'payment' if it's a one-time purchase
                    success_url=url_for('auth.stripe_success', _external=True) + "?session_id={CHECKOUT_SESSION_ID}",
                    cancel_url=url_for('auth.choose_plan', _external=True),
                )
                return redirect(checkout_session.url)
            except Exception as e:
                print(f"Stripe error: {e}")
                flash("An error occurred while creating the Stripe checkout session. Please try again.", "danger")

                return redirect(url_for('auth.choose_plan'))

        elif plan == 'student':
            current_user.plan = Plans.Student.value
            db_session.commit()
            flash("You've successfully selected the Student plan!", "success")
            return redirect(url_for('auth.introduction'))

        else:
            flash("Please select a valid plan option.", "warning")

    return render_template('auth/register_step2.html')


# Login
@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        flash("You are already logged in.", "info")
        if current_user.role == Role.User.value:
            return redirect(url_for("dashboard.dashboard"))
        elif current_user.role == Role.Manager.value:
            return redirect(url_for("academia.panel"))
        else:
            return redirect(url_for("admin.panel"))

    if request.method == "POST":
        db_session = get_db_session()
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        user = db_session.query(User).filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password) and user.active:
            user.last_sign_in = int(datetime.now(timezone.utc).timestamp() * 1000)
            db_session.commit()
            login_user(user)
            DiscordService.send_message(f"A new user has signed in: {user.email} (ID: {user.id})")

            if user.role == Role.User.value:
                return redirect(url_for("dashboard.dashboard"))
            elif user.role == Role.Manager.value:
                return redirect(url_for("academia.panel"))
            else:
                return redirect(url_for("admin.panel"))
        else:
            return render_template("auth/login.html", error="Invalid email or password.")

    return render_template("auth/login.html")


# Logout
@bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You’ve been logged out.", "info")
    return redirect(url_for("auth.login"))


@bp.route('/stripe-success')
@login_required
def stripe_success():
    try:
        session_id = request.args.get("session_id")
        if not session_id:
            flash("Missing session ID in Stripe redirect.", "danger")
            return redirect(url_for('auth.introduction'))

        session = stripe.checkout.Session.retrieve(session_id)

        if session["payment_status"] != "paid" or session["status"] != "complete":
            flash("Payment was not successful. Please try again.", "danger")
            return redirect(url_for("auth.introduction"))

        subscription_id = session.get("subscription")
        if not subscription_id:
            flash("No subscription found in the session.", "danger")
            return redirect(url_for('auth.introduction'))

        db_session = get_db_session()
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
                item = subscription["items"]["data"][0]
                current_user.stripe_subscription_expires_at = int(item["current_period_end"] * 1000)
                current_user.stripe_subscription_item_ids = ",".join(price_ids)
                current_user.stripe_subscription_canceled = bool(subscription["cancel_at_period_end"])
                db_session.commit()
                flash(f"Your {current_user.plan} subscription is now active!", "success")
            else:
                flash("No subscription items found. Contact support.", "danger")

        except Exception as e:
            print(subscription)
            print("Error processing subscription items:", e)
            flash("There was an issue processing your subscription. Please contact support.", "danger")

    except Exception as e:

        print("Stripe post-checkout error:", e)
        flash("There was an issue activating your plan. Please contact support.", "danger")

    return redirect(url_for('auth.introduction'))


@bp.route('/introduction')
@login_required
def introduction():
    return render_template('auth/register_step3.html', user=current_user)
