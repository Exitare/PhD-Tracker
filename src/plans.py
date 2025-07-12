import os
from enum import Enum
from typing import List


class Plans(Enum):
    Student = "student"
    StudentPlus = "student_plus"
    StudentPro = "student_pro"
    CustomPlan = "custom_plan"

    @classmethod
    def get_plan_name(cls, price_ids: List[str]) -> str:
        # Known Stripe price ID to Plan mapping
        stripe_price_map = {
            os.environ.get("STUDENT_PLUS_PRICE_ID"): cls.StudentPlus,
            os.environ.get("STUDENT_PRO_PRICE_ID"): cls.StudentPro,
        }

        if not price_ids:
            return cls.Student.value  # No subscription → free plan

        # Resolve each price_id to a Plan, or CustomPlan if unknown
        plans = [stripe_price_map.get(pid, cls.CustomPlan) for pid in price_ids]

        plan_priority = {
            cls.Student: 0,
            cls.StudentPlus: 1,
            cls.StudentPro: 2,
            cls.CustomPlan: -1,  # fallback, always lowest
        }

        highest_plan = max(plans, key=lambda plan: plan_priority[plan])
        return highest_plan.value


class StripeMeter(Enum):
    TokenRequests = "tokenrequests"
