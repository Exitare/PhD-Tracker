from flask import Blueprint, request, abort
from src import db_session
from src.db.models import User, StripeWebhookEvent
from datetime import datetime, timezone
import stripe
import os
from src.plans import Plans
from typing import List
from src.extensions import csrf
from src.role import Role
import logging

from src.services import MailService

bp = Blueprint("stripe_webhooks", __name__)

# Set your Stripe secret and webhook secret
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")


@bp.route("/webhooks", methods=["POST"])
@csrf.exempt
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get("stripe-signature")

    # Verify Stripe signature
    try:
        print("Verifying Stripe webhook signature...")
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.error.SignatureVerificationError):
        print("Invalid payload or signature verification failed.")
        abort(400)

    event_id: str = event["id"]

    # Check for duplicate events
    if db_session.query(StripeWebhookEvent).filter_by(event_id=event_id).first():
        print(f"Duplicate webhook event received: {event_id}")
        return "Duplicate webhook", 200

    event_type = event["type"]
    data = event["data"]["object"]

    # Optional: extract user by customer ID
    customer_id = data.get("customer")
    user: User = db_session.query(User).filter_by(stripe_customer_id=customer_id).first()
    if not user:
        print(f"No user found for customer ID: {customer_id}, when handling event: {event_type}")
        # If no user found, we can either create a new user or ignore this event
        # For now, we will ignore it
        return "User not found", 200

    if event_type == "customer.subscription.created":
        user.stripe_subscription_id = data.get("id")
        # Extract all price IDs from the subscription items
        price_ids: List[str] = [item["price"]["id"] for item in data["items"]["data"]]
        user.subscription_expires_at = int(data["current_period_end"]) * 1000
        user.stripe_subscription_item_ids = ",".join(price_ids)
        # Determine the highest plan based on price IDs
        user.plan = Plans.get_plan_name(price_ids)
        user.stripe_subscription_canceled = False

        if user.role == Role.Manager.value:
            logging.debug(f"Updating managed users for manager: {user.email} due to subscription deletion.")
            # If the user is a manager, we need to deactivate all managed users
            managed_users = db_session.query(User).filter_by(managed_by=user.id).all()
            for managed_user in managed_users:
                managed_user.managed_by_license_active = True
                managed_user.plan = user.plan
                managed_user.stripe_subscription_canceled = False

    elif event_type == "customer.subscription.updated":
        user.subscription_expires_at = int(data["current_period_end"]) * 1000
        # Extract all price IDs from the subscription items
        price_ids: List[str] = [item["price"]["id"] for item in data["items"]["data"]]
        # Determine the highest plan based on price IDs
        user.plan = Plans.get_plan_name(price_ids)
        user.stripe_subscription_id = data.get("id")
        user.stripe_subscription_item_ids = ",".join(price_ids)

        # if the subscription is canceled, we set the plan to Student, cancel at period end
        cancel_at_period_end = data.get("cancel_at_period_end", False)
        user.stripe_subscription_canceled = cancel_at_period_end

        if user.role == Role.Manager.value:
            logging.debug(f"Updating managed users for manager: {user.email} due to subscription deletion.")
            # If the user is a manager, we need to deactivate all managed users
            managed_users = db_session.query(User).filter_by(managed_by=user.id).all()
            for managed_user in managed_users:
                managed_user.managed_by_license_active = True
                managed_user.plan = user.plan
                managed_user.stripe_subscription_canceled = cancel_at_period_end


    elif event_type == "customer.subscription.deleted":
        user.subscription_expires_at = int(datetime.now(timezone.utc).timestamp() * 1000)
        user.plan = Plans.Student.value
        user.stripe_subscription_id = None
        user.stripe_subscription_item_ids = None
        user.stripe_subscription_canceled = False

        if user.role == Role.Manager.value:
            logging.debug(f"Updating managed users for manager: {user.email} due to subscription deletion.")
            # If the user is a manager, we need to deactivate all managed users
            managed_users = db_session.query(User).filter_by(managed_by=user.id).all()
            for managed_user in managed_users:
                managed_user.managed_by_license_active = False
                managed_user.plan = Plans.Student.value
                managed_user.stripe_subscription_canceled = False


    elif event_type == "invoice.payment_succeeded":
        subscription_id = data.get("subscription")
        if subscription_id and user and user.stripe_subscription_id == subscription_id:
            price_ids: List[str] = [item["price"]["id"] for item in data["items"]["data"]]
            # Determine the highest plan based on price IDs
            user.plan = Plans.get_plan_name(price_ids)
            user.stripe_subscription_id = subscription_id
            user.stripe_subscription_item_ids = ",".join(price_ids)
            user.subscription_expires_at = int(data["lines"]["data"][0]["period"]["end"]) * 1000
            user.stripe_subscription_canceled = False

            if user.role == Role.Manager.value:
                logging.debug(f"Updating managed users for manager: {user.email} due to subscription deletion.")
                # If the user is a manager, we need to deactivate all managed users
                managed_users = db_session.query(User).filter_by(managed_by=user.id).all()
                for managed_user in managed_users:
                    managed_user.managed_by_license_active = True
                    managed_user.plan = user.plan
                    managed_user.stripe_subscription_canceled = False


    elif event_type == "invoice.payment_failed":
        user.subscription_expires_at = int(datetime.now(timezone.utc).timestamp() * 1000)
        user.plan = Plans.Student.value
        user.stripe_subscription_id = None
        user.stripe_subscription_item_ids = None
        db_session.add(user)
        MailService.send_payment_failed_email(user)

        if user.role == Role.Manager.value:
            logging.debug(f"Updating managed users for manager: {user.email} due to subscription deletion.")
            # If the user is a manager, we need to deactivate all managed users
            managed_users = db_session.query(User).filter_by(managed_by=user.id).all()
            for managed_user in managed_users:
                managed_user.managed_by_license_active = False
                managed_user.plan = Plans.Student.value
                managed_user.stripe_subscription_canceled = False

    # Save webhook event log
    log = StripeWebhookEvent(
        event_id=event_id,
        event_type=event_type,
        received_at=int(datetime.now(timezone.utc).timestamp() * 1000),
    )
    db_session.add(log)
    db_session.commit()

    return "Success", 200
