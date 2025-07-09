from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from flask_login import login_required, current_user, login_user
from src import db_session
from src.db.models import User
from datetime import datetime, timezone
import stripe
from src.services import MailService, UserService
from src.role import Role
from werkzeug.security import generate_password_hash, check_password_hash
from src.forms import EmailForm, PasswordForm, ThemeForm

bp = Blueprint('academia', __name__)


@bp.route("/academia")
def view():
    return render_template('academia/academia.html')


@bp.route("/academia/register", methods=["POST", "GET"])
def register():
    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        org_name = request.form.get("org_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password: str = request.form.get("password", "").strip()

        # Input validation
        if not first_name or not last_name or not org_name or not email or not password:
            error = "All fields are required."
            return render_template("academia/register.html", error=error)

        # TODO: Add email format validation regex if needed

        # Check if user already exists
        existing_user = db_session.query(User).filter_by(email=email).first()
        if existing_user:
            error = "If the email is valid and available, you'll receive a confirmation shortly."
            return render_template("academia/register.html", error=error)

        try:
            # Create Stripe customer first
            stripe_customer = stripe.Customer.create(email=email)

            # create a unique access code
            access_code = UserService.create_access_token()

            user = User(
                password_hash=generate_password_hash(password),
                stripe_customer_id=stripe_customer.id,
                first_name=first_name,
                last_name=last_name,
                organization_name=org_name,
                email=email,
                created_at=int(datetime.now(timezone.utc).timestamp() * 1000),
                role=Role.Manager.value,
                access_code=access_code,
            )

            db_session.add(user)
            db_session.commit()

            MailService.send_academia_confirmation_email(user)

            # login the user

            login_user(user)
            return redirect(url_for("academia.panel"))

        except Exception as e:
            db_session.rollback()
            print(f"Academia registration error: {e}")
            error = "An error occurred during submission. Please try again later."
            return render_template("academia/signup.html", error=error)

    return render_template('academia/signup.html')


@bp.route("/academia/panel")
@login_required
def panel():
    if not UserService.can_access_page(current_user, allowed_roles=[Role.Manager.value]):
        flash("You do not have permission to view this page.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    email_form = EmailForm()
    password_form = PasswordForm()
    theme_form = ThemeForm()

    # Set the currently selected theme in the form
    current_theme = session.get('theme', 'lavender')
    theme_form.theme.data = current_theme

    # Fetch all users managed by the current user
    managed_users = db_session.query(User).filter_by(managed_by=current_user.id).all()

    return render_template('academia/account.html',
                           managed_users=managed_users,
                           email_form=email_form,
                           password_form=password_form,
                           theme_form=theme_form,
                           user=current_user)
