from flask import Blueprint, request, abort
from src.db import get_db_session
from src.db.models import User, StripeWebhookEvent
from datetime import datetime, timezone
import stripe
import os
from src.plans import Plans
from typing import List
from src.extensions import csrf
from src.role import Role
import logging

logger = logging.getLogger(__name__)

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
        logger.debug("Verifying Stripe webhook signature...")
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.error.SignatureVerificationError):
        logger.warning("Invalid payload or signature verification failed.")
        abort(400)

    event_id: str = event["id"]
    db_session = get_db_session()

    # Check for duplicate events
    if db_session.query(StripeWebhookEvent).filter_by(event_id=event_id).first():
        logger.debug(f"Duplicate webhook event received: {event_id}")
        return "Duplicate webhook", 200

    event_type = event["type"]
    data = event["data"]["object"]

    # Optional: extract user by customer ID
    customer_id = data.get("customer")
    user: User = db_session.query(User).filter_by(stripe_customer_id=customer_id).first()
    if not user:
        logger.debug(f"No user found for customer ID: {customer_id}, when handling event: {event_type}")
        # If no user found, we can either create a new user or ignore this event
        # For now, we will ignore it
        return "User not found", 200

    if event_type == "customer.subscription.created":
        user.stripe_subscription_id = data.get("id")
        # Extract all price IDs from the subscription items
        price_ids: List[str] = [item["price"]["id"] for item in data["items"]["data"]]
        user.stripe_subscription_expires_at = int(data["current_period_end"]) * 1000
        user.stripe_subscription_item_ids = ",".join(price_ids)
        # Determine the highest plan based on price IDs
        user.plan = Plans.get_plan_name(price_ids)
        user.stripe_subscription_canceled = False

        if user.role == Role.Manager.value:
            logging.debug(f"Updating managed users for manager: {user.email} due to subscription deletion.")
            # If the user is a manager, we need to deactivate all managed users
            managed_users = db_session.query(User).filter_by(managed_by=user.id).all()
            for managed_user in managed_users:
                managed_user.plan = user.plan
                managed_user.stripe_subscription_canceled = False

    elif event_type == "customer.subscription.updated":
        # Extract all price IDs from the subscription items
        price_ids: List[str] = [item["price"]["id"] for item in data["items"]["data"]]
        # Determine the highest plan based on price IDs
        user.plan = Plans.get_plan_name(price_ids)
        user.stripe_subscription_id = data.get("id")
        user.stripe_subscription_item_ids = ",".join(price_ids)

        # if the subscription is canceled, we set the plan to Student, cancel at period end
        user.stripe_subscription_expires_at = int(data["current_period_end"]) * 1000
        cancel_at_period_end = data.get("cancel_at_period_end", False)
        user.stripe_subscription_canceled = cancel_at_period_end

        if user.role == Role.Manager.value:
            logging.debug(f"Updating managed users for manager: {user.email} due to subscription deletion.")
            # If the user is a manager, we need to deactivate all managed users
            managed_users = db_session.query(User).filter_by(managed_by=user.id).all()
            for managed_user in managed_users:
                managed_user.plan = user.plan
                managed_user.stripe_subscription_canceled = cancel_at_period_end


    elif event_type == "customer.subscription.deleted":
        user.stripe_subscription_expires_at = int(datetime.now(timezone.utc).timestamp() * 1000)
        user.plan = Plans.Student.value
        user.stripe_subscription_id = None
        user.stripe_subscription_item_ids = None
        user.stripe_subscription_canceled = False

        if user.role == Role.Manager.value:
            logging.debug(f"Updating managed users for manager: {user.email} due to subscription deletion.")
            # If the user is a manager, we need to deactivate all managed users
            managed_users = db_session.query(User).filter_by(managed_by=user.id).all()
            for managed_user in managed_users:
                managed_user.plan = Plans.Student.value
                managed_user.stripe_subscription_canceled = False



    elif event_type == "checkout.session.completed":
        subscription_id = data.get("subscription")
        customer_id = data.get("customer")

        if not subscription_id or not customer_id:
            logging.warning("Subscription or customer ID missing in checkout.session.completed")
            return "", 200

        # Fetch subscription from Stripe to get line items and price info

        subscription = stripe.Subscription.retrieve(subscription_id)
        price_ids: List[str] = [item["price"]["id"] for item in subscription["items"]["data"]]

        # Fetch user from your DB
        user = db_session.query(User).filter_by(stripe_customer_id=customer_id).first()
        if user:
            user.plan = Plans.get_plan_name(price_ids)
            user.stripe_subscription_id = subscription_id
            user.stripe_subscription_item_ids = ",".join(price_ids)
            user.stripe_subscription_expires_at = int(subscription["current_period_end"]) * 1000
            user.stripe_subscription_canceled = False

            if user.role == Role.Manager.value:
                logging.debug(f"Updating managed users for manager: {user.email} after checkout session.")
                managed_users = db_session.query(User).filter_by(managed_by=user.id).all()

                for managed_user in managed_users:
                    managed_user.plan = user.plan
                    managed_user.stripe_subscription_canceled = False



    elif event_type == "invoice.payment_failed":
        if user:
            user.stripe_subscription_expires_at = int(datetime.now(timezone.utc).timestamp() * 1000)
            user.plan = Plans.Student.value
            user.stripe_subscription_id = None
            user.stripe_subscription_item_ids = None
            user.stripe_subscription_canceled = True

            if user.role == Role.Manager.value:
                logging.debug(f"Updating managed users for manager: {user.email} due to subscription failure.")
                managed_users = db_session.query(User).filter_by(managed_by=user.id).all()

                for managed_user in managed_users:
                    managed_user.plan = Plans.Student.value
                    managed_user.stripe_subscription_canceled = True


            db_session.commit()
            MailService.send_payment_failed_email(user)

        else:

            logging.warning("invoice.payment_failed event received but user not found.")

    # Save webhook event log
    log = StripeWebhookEvent(
        event_id=event_id,
        event_type=event_type,
        received_at=int(datetime.now(timezone.utc).timestamp() * 1000),
    )
    db_session.add(log)
    db_session.commit()

    return "Success", 200
