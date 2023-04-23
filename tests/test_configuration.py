import unittest

from accounts.metadata import *
from tests.test_config import create_savings_account


class TestConfiguration(unittest.TestCase):
    def test_serialize(self):
        account_type = create_savings_account()

        # serialize config to text using Pydantic

        text = account_type.json()

        account_type2 = AccountType.parse_raw(text)

        text2 = account_type2.json()

        self.assertEqual(text, text2)


class RateTest(unittest.TestCase):
    def test_get_max_when_empy(self):
        rate_type = RateType(name='rates', label='Rates')

        max_value = rate_type.get_max_to_amount()

        self.assertEqual(Decimal(0), max_value)

    def test_get_max_when_non_empy(self):
        rate_type = RateType(name='rates', label='Rates')

        rate_type.add_tier(Decimal(100), Decimal(5))

        max_value = rate_type.get_max_to_amount()

        self.assertEqual(Decimal(100), max_value)


if __name__ == '__main__':
    unittest.main()
