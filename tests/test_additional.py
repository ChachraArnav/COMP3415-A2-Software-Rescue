
from pathlib import Path
import tempfile
import unittest

from supplydesk.service import OrderService


class AdditionalTests(unittest.TestCase):

    def setUp(self):
        # Each test uses a separate temporary save file.
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "state.json"
        self.service = OrderService(self.path)

    def test_valid_order_reduces_stock(self):
        before = self.service.catalog()
        original_stock = next(
            p["stock"] for p in before
            if p["product_id"] == "notebook"
        )

        order = self.service.place_order(
            "regular",
            [{"product_id": "notebook", "quantity": 2}]
        )

        after = self.service.catalog()
        new_stock = next(
            p["stock"] for p in after
            if p["product_id"] == "notebook"
        )

        self.assertEqual(order["status"], "placed")
        self.assertEqual(order["total_cents"], 1000)
        self.assertEqual(new_stock, original_stock - 2)

    def test_zero_quantity_rejected(self):
        with self.assertRaises(ValueError):
            self.service.quote(
                "regular",
                [{"product_id": "notebook", "quantity": 0}]
            )

    def test_quantity_100_rejected(self):
        with self.assertRaises(ValueError):
            self.service.quote(
                "regular",
                [{"product_id": "notebook", "quantity": 100}]
            )

    def test_quantity_one_accepted(self):
        result = self.service.quote(
            "regular",
            [{"product_id": "notebook", "quantity": 1}]
        )
        self.assertEqual(result["subtotal_cents"], 500)

    def test_unknown_product_rejected(self):
        with self.assertRaises(ValueError):
            self.service.place_order(
                "regular",
                [{"product_id": "unknown-item", "quantity": 1}]
            )

    def test_invalid_customer_rejected(self):
        with self.assertRaises(ValueError):
            self.service.quote(
                "guest",
                [{"product_id": "notebook", "quantity": 1}]
            )

    def test_insufficient_stock_rejected(self):
        with self.assertRaises(ValueError):
            self.service.place_order(
                "regular",
                [{"product_id": "hoodie", "quantity": 6}]
            )

        self.assertEqual(self.service.list_orders(), [])
        hoodie = next(
            p for p in self.service.catalog()
            if p["product_id"] == "hoodie"
        )
        self.assertEqual(hoodie["stock"], 5)

    def test_quote_does_not_change_stock(self):
        before = self.service.catalog()

        self.service.quote(
            "regular",
            [{"product_id": "notebook", "quantity": 2}]
        )

        self.assertEqual(self.service.catalog(), before)
        self.assertEqual(self.service.list_orders(), [])

    def test_student_discount_at_exactly_50(self):
        # Two canvas bags cost $50.00.
        result = self.service.quote(
            "student",
            [{"product_id": "bag", "quantity": 2}]
        )

        self.assertEqual(result["subtotal_cents"], 5000)
        self.assertEqual(result["discount_cents"], 500)
        self.assertEqual(result["total_cents"], 4500)

    def test_double_cancellation_does_not_restore_twice(self):
        before = self.service.catalog()

        order = self.service.place_order(
            "regular",
            [{"product_id": "notebook", "quantity": 2}]
        )

        self.service.cancel_order(order["order_id"])
        self.service.cancel_order(order["order_id"])

        self.assertEqual(self.service.catalog(), before)


if __name__ == "__main__":
    unittest.main()
