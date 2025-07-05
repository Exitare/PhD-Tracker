import os
from enum import Enum
from typing import List

class Plans(Enum):
    Student = "student"
    StudentPlus = "student_plus"
    StudentPro = "student_pro"

    @classmethod
    def from_stripe_price_id(cls, price_id: str) -> str:
        stripe_price_map = {
            "": cls.Student,
            os.environ.get("STUDENT_PLUS_PRICE_ID"): cls.StudentPlus,

        }
        plan = stripe_price_map.get(price_id)
        return plan.value if plan else cls.Student.value  # fallback

    @classmethod
    def get_plan_name(cls, price_ids: List[str]) -> str:
        stripe_price_map = {
            "": cls.Student,
            os.environ.get("STUDENT_PLUS_PRICE_ID"): cls.StudentPlus,
            os.environ.get("STUDENT_PRO_PRICE_ID"): cls.StudentPro,
        }

        print(price_ids)
        print(stripe_price_map)

        print(price_ids)
        # Map each price ID to a Plan Enum, default to Student if not found
        plans = [stripe_price_map.get(pid, cls.Student) for pid in price_ids]

        # Choose the "highest" plan based on their enum order
        highest_plan = max(plans, key=lambda plan: list(cls).index(plan))

        print(highest_plan)


        return highest_plan.value


class StripeMeter(Enum):
    TokenRequests = "tokenrequests"
