from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import current_user, login_required, logout_user
from src.db.models import User
import stripe
from src.role import Role
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

from src.db import get_db_session
from src.services import UserService

bp = Blueprint("admin", __name__)


@bp.route("/admin/users", methods=["GET"])
@login_required
def manage_users():
    db_session = get_db_session()
    user: User = db_session.query(User).filter_by(email=current_user.email).first()

    if not user or not UserService.can_access_page(user, allowed_roles=[Role.Admin.value]):
        flash("You do not have permission to access this page.", "danger")
        logout_user()
        return redirect(url_for("auth.login"))

    all_users = db_session.query(User).all()
    display_users = []
    for tmp_user in all_users:
        display_users.append({
            "id": tmp_user.id,
            "email": tmp_user.email,
            "role": tmp_user.role,
            "created_at": tmp_user.created_at,
            "active": tmp_user.active,
            "stripe_customer_id": tmp_user.stripe_customer_id
        })

    return render_template('admin/user_management.html', users=display_users)


@bp.route("/admin", methods=["GET"])
@login_required
def dashboard():
    db_session = get_db_session()
    user: User = db_session.query(User).filter_by(email=current_user.email).first()

    if not user or not UserService.can_access_page(user=user, allowed_roles=[Role.Admin.value]):
        flash("You do not have permission to access this page.", "danger")
        logout_user()
        return redirect(url_for("auth.login"))

    all_users = db_session.query(User).all()
    display_users = []
    for tmp_user in all_users:
        display_users.append({
            "id": tmp_user.id,
            "email": tmp_user.email,
            "role": tmp_user.role,
            "created_at": tmp_user.created_at,
            "active": tmp_user.active,
            "stripe_customer_id": tmp_user.stripe_customer_id
        })

    return render_template('admin/admin_base.html')


@bp.route("/admin/price", methods=["GET", "POST"])
@login_required
def manage_prices():
    db_session = get_db_session()
    user: User = db_session.query(User).filter_by(email=current_user.email).first()

    if not UserService.can_access_page(user=user, allowed_roles=[Role.Admin.value]):
        flash("You do not have permission to access this page.", "danger")
        logout_user()
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        pricing_type = request.form.get("pricing_type")
        interval = request.form.get("interval")
        description = request.form.get("description")
        product_id = "prod_SZbBNUzElOhpI9"

        if pricing_type == "flat":
            amount_str = request.form.get("amount")
            amount = parse_dollar_amount(amount_str)

            stripe.Price.create(
                unit_amount=amount,
                currency="usd",
                recurring={"interval": interval},
                product=product_id,
                nickname=description,
            )
        else:
            try:
                tier_1_max = int(request.form.get("tier_1_max").replace(",", ""))
                tier_1_amount = request.form.get("tier_1_unit_amount").replace(",", "")
                tier_2_amount = request.form.get("tier_2_unit_amount").replace(",", "")

                stripe.Price.create(
                    currency="usd",
                    recurring={"interval": interval},
                    product=product_id,
                    nickname=description,
                    billing_scheme="tiered",
                    tiers_mode="volume",
                    tiers=[
                        {
                            "up_to": tier_1_max,
                            "unit_amount_decimal": dollars_to_cents_str(tier_1_amount),
                        },
                        {
                            "up_to": "inf",
                            "unit_amount_decimal": dollars_to_cents_str(tier_2_amount),
                        }
                    ]
                )
            except (InvalidOperation, ValueError):
                flash("Invalid input in tier values. Please double-check your numbers.", "danger")

        flash("Price created successfully!", "success")
        return redirect(url_for("admin.manage_prices"))

    prices = stripe.Price.list()
    pr = []
    for price in prices.data:
        if price.nickname and "SG" in price.nickname:
            continue
        pr.append({
            "id": price.id,
            "active": price.active,
            "unit_amount": price.unit_amount,
            "currency": price.currency,
            "nickname": price.nickname,
            "recurring": price.recurring
        })

    return render_template('admin/price_management.html', prices=pr)


@bp.route("/admin/archive-price/<price_id>", methods=["POST"])
@login_required  # If you use login
def archive_price(price_id):
    try:
        stripe.Price.modify(price_id, active=False)
        flash("Price archived successfully.", "success")
    except Exception as e:
        flash(f"Error archiving price: {e}", "danger")
    return redirect(url_for("admin.manage_prices"))


@bp.route("/admin/users/status/<int:user_id>", methods=["POST"])
@login_required
def toggle_user_status(user_id: int):
    db_session = get_db_session()
    user: User = db_session.query(User).filter_by(email=current_user.email).first()

    if not UserService.can_access_page(user=user, allowed_roles=[Role.Admin.value]):
        flash("You do not have permission to access this page.", "danger")
        logout_user()
        return redirect(url_for("auth.login"))

    # change active to false
    target_user = db_session.query(User).filter_by(id=user_id).first()
    if not target_user:
        logger.debug(f"User with ID {user_id} not found.")
        flash("User not found.", "danger")
        return redirect(request.referrer or url_for("admin.dashboard"))

    if target_user.active:
        target_user.active = False
        target_user.deactivated_at = int(datetime.now(timezone.utc).timestamp() * 1000)
        db_session.commit()
        flash(f"User {target_user.email} has been deactivated.", "success")
        return redirect(request.referrer or url_for("admin.dashboard"))
    else:
        target_user.active = True
        target_user.deactivated_at = None
        db_session.commit()
        flash(f"User {target_user.email} has been reactivated.", "success")
        # redirect to referer page
        return redirect(request.referrer or url_for("admin.dashboard"))


def parse_dollar_amount(value_str):
    """Converts string dollar input to integer cents."""
    clean = value_str.replace(",", "").strip()
    return int(round(float(clean) * 100))


def dollars_to_cents_str(d):
    return str((Decimal(d) * 100).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))
