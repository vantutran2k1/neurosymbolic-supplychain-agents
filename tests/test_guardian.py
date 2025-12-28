import unittest

from src.guardian.schemas import GuardianContext, Proposal, ProductionRecipe
from src.guardian.solver import SymbolicGuardian


class TestSymbolicGuardian(unittest.TestCase):
    def setUp(self):
        self.guardian = SymbolicGuardian()

        self.recipe = ProductionRecipe(
            process_id="make_B", inputs={"product_A": 2}, outputs={"product_B": 1}
        )

        self.context = GuardianContext(
            agent_id="agent_1",
            step=1,
            balance=1000.0,
            inventory={"product_A": 10, "product_B": 0},
            capacity=100,
            recipes=[self.recipe],
        )

    def test_buying_insufficient_funds(self):
        prop = Proposal(
            partner_id="p1",
            product_id="product_A",
            quantity=100,
            unit_price=20.0,
            is_buying=True,
        )

        is_valid, reason = self.guardian.validate(self.context, prop)
        self.assertFalse(is_valid)
        self.assertIn("insufficient_funds", reason)

        corrected = self.guardian.suggest_correction(self.context, prop)
        self.assertEqual(corrected.quantity, 50)

    def test_selling_with_production(self):
        prop_ok = Proposal(
            partner_id="p1",
            product_id="product_B",
            quantity=5,
            unit_price=100,
            is_buying=False,
        )
        self.assertTrue(self.guardian.validate(self.context, prop_ok)[0])

        prop_fail = Proposal(
            partner_id="p1",
            product_id="product_B",
            quantity=6,
            unit_price=100,
            is_buying=False,
        )
        is_valid, reason = self.guardian.validate(self.context, prop_fail)
        self.assertFalse(is_valid)
        self.assertIn("insufficient_stock_or_production_capacity", reason)


if __name__ == "__main__":
    unittest.main()
