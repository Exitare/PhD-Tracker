# routes/auth.py
from datetime import datetime, timezone
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from src.db.models import User
from src.db import db_session
from flask_login import login_required, current_user
import stripe
import os

stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
print("Stripe API Key:", stripe.api_key)

bp = Blueprint("auth", __name__)


# Register
@bp.route('/register', methods=['GET', 'POST'])
def register_step1():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # Input validation
        if not email or not password:
            error = "Email and password are required."
            return render_template('auth/register_step1.html', error=error, email=email)

        # Check if user already exists
        existing_user = db_session.query(User).filter_by(email=email).first()
        if existing_user:
            error = "Email already registered."
            return render_template('auth/register_step1.html', error=error, email=email)

        try:
            # Create Stripe customer first
            stripe_customer = stripe.Customer.create(email=email)

            # Then create user and assign stripe_customer_id
            user = User(
                email=email,
                password_hash=generate_password_hash(password),
                stripe_customer_id=stripe_customer.id,
                created_at=int(datetime.now(timezone.utc).timestamp() * 1000)
            )
            db_session.add(user)
            db_session.commit()

            login_user(user)
            return redirect(url_for('auth.choose_plan'))

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
        plan = request.form.get('plan')

        if plan == 'student_plus':
            if not current_user.stripe_customer_id:
                flash("Stripe customer not found for this account.", "danger")
                return redirect(url_for('auth.choose_plan'))

            try:
                checkout_session = stripe.checkout.Session.create(
                    customer=current_user.stripe_customer_id,
                    payment_method_types=['card'],
                    line_items=[{
                        'price': "price_1ReRzTDanNlk6y5aszKHM0mU",
                    }],
                    mode='subscription',  # change to 'payment' if it's a one-time purchase
                    success_url=url_for('auth.stripe_success', _external=True) + "?session_id={CHECKOUT_SESSION_ID}",
                    cancel_url=url_for('auth.choose_plan', _external=True),
                )
                return redirect(checkout_session.url)
            except Exception as e:
                print(f"Stripe error: {e}")
                # set customer plan to 'student' if checkout fails
                current_user.plan = 'student'
                db_session.commit()

                return redirect(url_for('auth.choose_plan'))

        elif plan == 'student':
            current_user.plan = 'student'
            db_session.commit()
            flash("You've successfully selected the Student plan!", "success")
            return redirect(url_for('dashboard.dashboard'))

        else:
            flash("Please select a valid plan option.", "warning")

    return render_template('auth/register_step2.html')


# Login
@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        user = db_session.query(User).filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for("dashboard.dashboard"))
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
            return redirect(url_for('dashboard.dashboard'))

        session = stripe.checkout.Session.retrieve(session_id)

        subscription_id = session.get("subscription")
        if not subscription_id:
            flash("No subscription found in the session.", "danger")
            return redirect(url_for('dashboard.dashboard'))

        subscription = stripe.Subscription.retrieve(subscription_id)

        # Get the first subscription item (usually one per sub)
        if subscription["items"]["data"]:
            item_id = subscription["items"]["data"][0]["id"]
            current_user.stripe_subscription_id = subscription_id
            current_user.stripe_subscription_item_id = item_id
            current_user.plan = 'student_plus'
            db_session.commit()
            flash("Your Student+ subscription is now active!", "success")
        else:
            flash("No subscription items found. Contact support.", "danger")

    except Exception as e:
        print("Stripe post-checkout error:", e)
        flash("There was an issue activating your plan. Please contact support.", "danger")

    return redirect(url_for('dashboard.dashboard'))
