import unittest
import os
from src.plans import Plans


class TestPlansEnum(unittest.TestCase):

    def setUp(self):
        # Set up mock environment variables for known price IDs
        os.environ["STUDENT_PLUS_PRICE_ID"] = "price_plus_123"
        os.environ["STUDENT_PRO_PRICE_ID"] = "price_pro_456"

    def test_no_price_ids_returns_student(self):
        self.assertEqual(Plans.get_plan_name([]), "student")

    def test_student_plus_price_id(self):
        self.assertEqual(Plans.get_plan_name(["price_plus_123"]), "student_plus")

    def test_student_pro_price_id(self):
        self.assertEqual(Plans.get_plan_name(["price_pro_456"]), "student_pro")

    def test_multiple_known_price_ids_returns_highest(self):
        # student_plus + student_pro → student_pro is higher
        self.assertEqual(Plans.get_plan_name(["price_plus_123", "price_pro_456"]), "student_pro")

    def test_unknown_price_id_returns_custom_plan(self):
        self.assertEqual(Plans.get_plan_name(["price_unknown_999"]), "custom_plan")

    def test_mixed_known_and_unknown_returns_custom_plan(self):
        self.assertEqual(Plans.get_plan_name(["price_pro_456", "price_unknown_999"]), "student_pro")

    def test_all_unknown_ids_returns_custom_plan(self):
        self.assertEqual(Plans.get_plan_name(["foo", "bar"]), "custom_plan")

    def test_all_unknown_id_returns_custom_plan(self):
        self.assertEqual(Plans.get_plan_name(["foo"]), "custom_plan")


if __name__ == '__main__':
    unittest.main()
