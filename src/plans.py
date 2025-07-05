import os
from enum import Enum


class Plans(Enum):
    Student = "student"
    StudentPlus = "student_plus"

    @classmethod
    def from_stripe_price_id(cls, price_id: str) -> str:
        stripe_price_map = {
            "": cls.Student,
            os.environ.get("STUDENT_PLUS_PRICE_ID"): cls.StudentPlus,
        }
        plan = stripe_price_map.get(price_id)
        return plan.value if plan else cls.Student.value  # fallback


class StripeMeter(Enum):
    TokenRequests = "tokenrequests"
