import unittest

from accounts.runtime import *
from tests.test_config import create_savings_account


def evaluate_account(account_type: AccountType, monthly_fee: Decimal, deposit: Decimal,
                     withholdingTax: Decimal) -> Account:
    account = Account(start_date=date(2019, 1, 1), account_type_name=account_type.name,
                      account_type=account_type,
                      properties={"monthlyFee": monthly_fee, "withholdingTax": withholdingTax})
    valuation = AccountValuation(account, account_type, date(2020, 1, 1))
    deposit_transaction_type = account_type.get_transaction_type("deposit")
    external_transactions = group_by_date([
        ExternalTransaction(transaction_type_name=deposit_transaction_type.name,
                            amount=deposit, value_date=date(2019, 1, 1))])
    valuation.forecast(date(2020, 1, 1), external_transactions)
    return account


class TestAccount(unittest.TestCase):
    def test_create_account(self):
        account_type = create_savings_account()

        account = Account(start_date=date.today(), account_type_name=account_type.name, account_type=account_type)

        self.assertEqual(3, len(account.positions.keys()))

        json = account.json()

        account2 = Account.parse_raw(json)

        self.assertEqual(account.start_date, account2.start_date)

    def test_eval(self):
        account_type = create_savings_account()

        account = Account(start_date=date(2019, 1, 1), account_type_name=account_type.name,
                          account_type=account_type)

        self.assertEqual(Decimal(0), account.evaluate("self.current", None))

        self.assertEqual(date(2019, 1, 1), account.evaluate("self.start_date", None))

        self.assertEqual(date(2019, 1, 1) + relativedelta(months=+1) + relativedelta(days=-1),
                         account.evaluate("self.start_date + relativedelta(months=+1) + relativedelta(days=-1)",
                                          None))

    def test_valuation(self):
        account_type = create_savings_account()

        account = evaluate_account(account_type, monthly_fee=Decimal(1), deposit=Decimal(1000), withholdingTax=Decimal(0.2))

        self.assertAlmostEqual(account.positions['current'].amount, Decimal(1018.24775), places=4)
        self.assertAlmostEqual(account.positions['withholding'].amount, Decimal(6.04955), places=4)
        self.assertAlmostEqual(account.transactions[1].amount, Decimal(0.08219), places=4)

    def test_valuation_difference(self):
        account_type = create_savings_account()

        original = evaluate_account(account_type, monthly_fee=Decimal(1),
                                    deposit=Decimal(1000), withholdingTax=Decimal(0.2)).transactions
        new = evaluate_account(account_type, monthly_fee=Decimal(0),
                               deposit=Decimal(1000), withholdingTax=Decimal(0.1)).transactions

        difference = valuation_difference(original, new)

        self.assertEqual(335, len(difference.keys()))

        diff: List[TransactionDifference] = difference[date(2019, 1, 31)]

        self.assertEqual(4, len(diff))

        fee = next(t for t in diff if t.transaction_type == 'fee')
        withholding = next(t for t in diff if t.transaction_type == 'withholdingTax')

        self.assertEqual(Decimal(-1), fee.amount)
        self.assertEqual(1, len(fee.original))
        self.assertEqual(0, len(fee.new))
        self.assertAlmostEqual(Decimal(-0.25477), withholding.amount, 3)


if __name__ == '__main__':
    unittest.main()
