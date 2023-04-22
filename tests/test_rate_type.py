import unittest
from datetime import date
from decimal import Decimal

from accounts.metadata import RateType


class TestRateType(unittest.TestCase):
    def setUp(self):
        self.payment_rates = RateType(name="payments", label="Wire Payment Tier Rates")
        self.payment_rates.add_tier(Decimal(10), Decimal(0))
        self.payment_rates.add_tier(Decimal(100), Decimal(5))
        self.payment_rates.add_tier(Decimal(1000), Decimal(4))
        self.payment_rates.add_tier(Decimal(1000000), Decimal(3))

    def test_get_rate(self):
        payment_rates = RateType(name="payments", label="Payment Rates")

        payment_rates.add_tier(Decimal(1000), Decimal(0))
        payment_rates.add_tier(Decimal(10000), Decimal(0.01))

        self.assertEqual(payment_rates.get_rate(Decimal(0.000000001)), Decimal(0))

    def test_get_fee_success(self):
        self.assertEqual(self.payment_rates.get_fee(Decimal(0), Decimal(5)), Decimal(0))
        self.assertEqual(self.payment_rates.get_fee(Decimal(5), Decimal(15)), Decimal(25))
        self.assertEqual(self.payment_rates.get_fee(Decimal(15), Decimal(55)), Decimal(200))
        self.assertEqual(self.payment_rates.get_fee(Decimal(55), Decimal(1005)), Decimal(3840))

    def test_get_daily_fee(self):
        rt_users = RateType(name="userRates", label="test")
        rt_users.add_tier(Decimal(3), Decimal(30))
        rt_users.add_tier(Decimal(10), Decimal(25))
        rt_users.add_tier(Decimal(1000), Decimal(10))

        value_date = date(2020, 4, 20)

        self.assertEqual(rt_users.get_daily_fee(Decimal(1), value_date), Decimal(1))
        self.assertEqual(rt_users.get_daily_fee(Decimal(5), value_date), Decimal(3 * 30 + 2 * 25) / (Decimal(30)))
        self.assertEqual(rt_users.get_daily_fee(Decimal(12), value_date),
                          Decimal(3 * 30 + 7 * 25 + 2 * 10) / Decimal(30))


if __name__ == '__main__':
    unittest.main()
