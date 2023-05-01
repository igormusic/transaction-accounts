import unittest
from datetime import date
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from accounts.metadata import AccountType
from accounts.runtime import Account, PropertyValue, AccountValuation, Schedule
from tests.test_config import create_loan_given_account


def create_without_mandatory_properties():
    account_type = create_loan_given_account()

    start_date = date(2013, 3, 8)
    end_date = start_date + relativedelta(years=+25)

    account = Account(start_date=start_date,
                      account_type_name=account_type.name,
                      account_type=account_type,
                      dates={"accrual_start": start_date,
                             "end_date": end_date}
                      )


class TestConfiguration(unittest.TestCase):

    def test_serialize(self):
        account_type = None

        with open('loan_given.json', 'r') as f:
            json_str = f.read()
            account_type = AccountType.parse_raw(json_str)

        start_date = date(2013, 3, 8)
        end_date = start_date + relativedelta(year=+25)

        parameters = {"advance_amount": 624000}

        account = Account(start_date=start_date,
                          account_type_name=account_type.name,
                          account_type=account_type,
                          dates={"accrual_start": start_date,
                                 "end_date": end_date}
                          )

        self.assertEqual(3, len(account.positions.keys()))

    def test_mandatory_properties(self):
        self.assertRaises(ValueError, create_without_mandatory_properties)

    def test_instalments(self):
        account_type = create_loan_given_account()

        start_date = date(2013, 3, 8)
        end_date = start_date + relativedelta(years=+25)

        dates = {"accrual_start": start_date,
                 "end_date": end_date}

        properties = {"advance": 624000,
                      "payment": 0}

        account = Account(start_date=start_date,
                          account_type_name=account_type.name,
                          account_type=account_type,
                          dates=dates,
                          properties=properties
                          )

        interest_start = date(2013, 3, 31)

        interest_schedule: Schedule = account.schedules["interest"]

        interest_schedule.start_date = interest_start
        interest_schedule.end_date = end_date
        interest_schedule.include_dates.append(end_date)

        redemption_schedule: Schedule =  account.schedules["redemption"]

        redemption_schedule.start_date = interest_start
        redemption_schedule.end_date = end_date
        redemption_schedule.include_dates.append(end_date)

        valuation = AccountValuation(account, account_type, end_date, True)

        valuation.forecast(end_date + relativedelta(days=1), [])

        self.assertEqual(5, len(account.positions.keys()))
        self.assertAlmostEqual(Decimal(1333778.93), account.positions["principal"].amount, places=2)
        self.assertAlmostEqual(Decimal(709778.93), account.positions["interest_capitalized"].amount, places=2)
        self.assertAlmostEqual(Decimal(0.005), account.positions["accrued"].amount, places=2)
