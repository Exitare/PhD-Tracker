from src.db.models import User
from src.plans import Plans, StripeMeter
from src.role import Role
import stripe


class UserService:

    @staticmethod
    def create_access_token():
        # create a 10 letter token
        import random
        import string
        return ''.join(random.choices(string.ascii_letters + string.digits, k=10))

    @staticmethod
    def can_access_page(user: User) -> bool:
        if user.managed_by is not None and not user.email_verified and not user.access_code:
            return False

        if user.role == Role.Manager.value:
            return False

        return True

    @staticmethod
    def can_use_ai(user: User) -> bool:
        """
        Check if the user can use AI features based on their plan and status.
        :param user:
        :return:
        """

        if user.role == Plans.StudentPlus.value:
            return True
        elif user.role == Plans.StudentPro.value:
            return True
        elif user.role == Plans.CustomPlan.value:
            return True

        if user.managed_by is not None and user.email_verified and user.active:
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
