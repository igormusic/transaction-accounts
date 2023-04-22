import unittest
from datetime import date
from decimal import Decimal

from accounts.metadata import Configuration
from accounts.runtime import *
from tests.test_config import create_savings_account


class TestAccount(unittest.TestCase):
    def test_create_account(self):
        config = create_savings_account()

        account_type = config.account_types[0]

        account = Account(date.today(), account_type, config)

        self.assertEqual(3, len(account.positions))

    def test_eval(self):
        config = create_savings_account()

        account_type = config.get_account_type("savingsAccount")
        account = Account(date(2019, 1, 1), account_type, config)

        self.assertEqual(Decimal(0), account.evaluate("self.current", None))

        self.assertEqual(date(2019, 1, 1), account.evaluate("self.start_date", None))

        self.assertEqual(date(2019, 1, 1) + relativedelta(months=+1) + relativedelta(days=-1),
                         account.evaluate("self.start_date + relativedelta(months=+1) + relativedelta(days=-1)",
                                          None))

    def test_valuation(self):
        config: Configuration = create_savings_account()

        # account = create_account(config, "savingsAccount", date(2019, 1, 1))
        account_type = config.get_account_type("savingsAccount")
        account = Account(date(2019, 1, 1), account_type, config)

        valuation = AccountValuation(account, account_type, config, date(2020, 1, 1))

        deposit_transaction_type = config.get_transaction_type("deposit")

        external_transactions = group_by_date([
            ExternalTransaction(deposit_transaction_type.name, Decimal(1000), date(2019, 1, 1))])

        valuation.forecast(date(2020, 1, 1), external_transactions)

        self.assertAlmostEqual(account.positions['current'].amount, Decimal(1030.41), places=1)
        self.assertAlmostEqual(account.positions['withholding'].amount, Decimal(30.41) * Decimal(0.2), places=1)


if __name__ == '__main__':
    unittest.main()
