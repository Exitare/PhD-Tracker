from src.db.models import User
from src.plans import Plans, StripeMeter
from src.role import Role
import stripe
import logging
from typing import List


class UserService:

    @staticmethod
    def create_access_token():
        # create a 10 letter token
        import random
        import string
        return ''.join(random.choices(string.ascii_letters + string.digits, k=10))

    @staticmethod
    def can_access_page(user: User, allowed_roles: List) -> bool:
        if not user:
            return False

        if user.managed_by is not None and not user.email_verified and not user.active:
            logging.debug(f"User {user.email} is managed by another user and has not verified their email or provided an access code.")
            return False

        if user.role in allowed_roles:
            return True

        return False

    @staticmethod
    def can_use_ai(user: User) -> bool:
        """
        Check if the user can use AI features based on their plan and status.
        :param user:
        :return:
        """

        if user.role == Plans.StudentPlus.value or user.role == Plans.StudentPro.value or user.role == Plans.CustomPlan.value:
            return True
        else:
            return False

    @staticmethod
    def report_usage(user: User, token_count: int) -> bool:
        managed_user: bool = user.managed_by is not None

        print(f"AI token usage: {token_count}, user is {'managed' if managed_user else 'not managed'} by another user.")

        # report usage
        stripe.billing.MeterEvent.create(
            event_name=StripeMeter.TokenRequests.value,
            payload={
                "value": str(token_count),
                "stripe_customer_id": user.managed_by_stripe_id if managed_user else user.stripe_customer_id,
            }
        )
        return True
