
"""Regression tests for CR-01 Express Delivery."""

import tempfile
import unittest
from pathlib import Path

from supplydesk.service import OrderService


class ExpressDeliveryTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.state_path = Path(self.temp_dir.name) / "state.json"
        self.service = OrderService(self.state_path)

    def test_regular_express_quote(self):
        quote = self.service.quote(
            "regular",
            [{"product_id": "notebook", "quantity": 2}],
            "express",
        )
        self.assertEqual(quote["subtotal_cents"], 1000)
        self.assertEqual(quote["discount_cents"], 0)
        self.assertEqual(quote["delivery_cents"], 1200)
        self.assertEqual(quote["total_cents"], 2200)

    def test_student_express_quote(self):
        quote = self.service.quote(
            "student",
            [{"product_id": "hoodie", "quantity": 2}],
            "express",
        )
        self.assertEqual(quote["subtotal_cents"], 8000)
        self.assertEqual(quote["discount_cents"], 800)
        self.assertEqual(quote["delivery_cents"], 1200)
        self.assertEqual(quote["total_cents"], 8400)

    def test_express_fee_never_waived(self):
        quote = self.service.quote(
            "regular",
            [{"product_id": "hoodie", "quantity": 3}],
            "express",
        )
        self.assertEqual(quote["delivery_cents"], 1200)
        self.assertEqual(quote["total_cents"], 13200)

    def test_standard_delivery_unchanged(self):
        quote = self.service.quote(
            "regular",
            [{"product_id": "hoodie", "quantity": 3}],
            "delivery",
        )
        self.assertEqual(quote["delivery_cents"], 0)
        self.assertEqual(quote["total_cents"], 12000)

    def test_pickup_unchanged(self):
        quote = self.service.quote(
            "regular",
            [{"product_id": "notebook", "quantity": 2}],
            "pickup",
        )
        self.assertEqual(quote["delivery_cents"], 0)
        self.assertEqual(quote["total_cents"], 1000)

    def test_invalid_fulfillment_rejected(self):
        with self.assertRaises(ValueError):
            self.service.quote(
                "regular",
                [{"product_id": "notebook", "quantity": 2}],
                "overnight",
            )

    def test_express_order_matches_quote(self):
        items = [{"product_id": "hoodie", "quantity": 2}]
        quote = self.service.quote("student", items, "express")
        order = self.service.place_order("student", items, "express")

        for key in (
            "customer_type",
            "fulfillment",
            "items",
            "subtotal_cents",
            "discount_cents",
            "delivery_cents",
            "total_cents",
        ):
            self.assertEqual(order[key], quote[key])

    def test_express_order_persists_after_reopening(self):
        order = self.service.place_order(
            "student",
            [{"product_id": "hoodie", "quantity": 2}],
            "express",
        )

        reopened_service = OrderService(self.state_path)
        saved_order = reopened_service.get_order(order["order_id"])

        self.assertEqual(saved_order, order)
        self.assertEqual(saved_order["fulfillment"], "express")
        self.assertEqual(saved_order["delivery_cents"], 1200)
        self.assertEqual(saved_order["total_cents"], 8400)

    def test_express_order_retains_details_after_cancellation(self):
        order = self.service.place_order(
            "student",
            [{"product_id": "hoodie", "quantity": 2}],
            "express",
        )

        cancelled = self.service.cancel_order(order["order_id"])

        self.assertEqual(cancelled["status"], "cancelled")
        self.assertEqual(cancelled["fulfillment"], "express")
        self.assertEqual(cancelled["items"], order["items"])
        self.assertEqual(cancelled["discount_cents"], 800)
        self.assertEqual(cancelled["delivery_cents"], 1200)
        self.assertEqual(cancelled["total_cents"], 8400)

        reopened = OrderService(self.state_path)
        saved = reopened.get_order(order["order_id"])
        self.assertEqual(saved, cancelled)


if __name__ == "__main__":
    unittest.main()
