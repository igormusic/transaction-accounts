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


def create_loan_account(account_type: AccountType, start_date: date) -> (Account, date):
    end_date = start_date + relativedelta(years=+25)
    dates = {"accrual_start": start_date,
             "end_date": end_date}
    properties = {"advance": 624000,
                  "payment": 0}

    # get initial values
    account = Account(start_date=start_date,
                      account_type_name=account_type.name,
                      account_type=account_type,
                      dates=dates,
                      properties=properties
                      )

    interest_start = date(2013, 3, 31)
    interest_schedule: Schedule = account.schedules["interest"]
    interest_schedule.cached_dates = {}
    interest_schedule.start_date = interest_start
    interest_schedule.end_date = end_date
    interest_schedule.include_dates.append(end_date)
    redemption_schedule: Schedule = account.schedules["redemption"]
    redemption_schedule.cached_dates = {}
    redemption_schedule.start_date = interest_start
    redemption_schedule.end_date = end_date
    redemption_schedule.include_dates.append(end_date)

    # create new account using schedules above

    account = Account(start_date=start_date,
                      account_type_name=account_type.name,
                      account_type=account_type,
                      dates=dates,
                      properties=properties,
                      schedules={"interest": interest_schedule,
                                 "redemption": redemption_schedule})

    dict = account.dict()
    json = account.json()

    return account, end_date


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

    def test_serialize_to_json(self):
        account_type = create_loan_given_account()

        json = account_type.json()

        self.assertIsNotNone(json)

        account_type2 = AccountType.parse_raw(json)

        json2 = account_type2.json()

        self.assertEqual(json, json2)

    def test_mandatory_properties(self):
        self.assertRaises(ValueError, create_without_mandatory_properties)

    def test_forecast(self):
        account_type = create_loan_given_account()

        account, end_date = create_loan_account(account_type, date(2013, 3, 8))

        valuation = AccountValuation(account=account, account_type=account_type, action_date=end_date, trace=True)

        valuation.forecast(end_date + relativedelta(days=1), [])

        self.assertEqual(5, len(account.positions.keys()))
        self.assertAlmostEqual(Decimal(1333778.93), account.positions["principal"].amount, places=2)
        self.assertAlmostEqual(Decimal(709778.93), account.positions["interest_capitalized"].amount, places=2)
        self.assertAlmostEqual(Decimal(0.005), account.positions["accrued"].amount, places=2)

    def test_installments(self):
        account_type = create_loan_given_account()

        account, end_date = create_loan_account(account_type, date(2013, 3, 8))

        valuation = AccountValuation(account=account, account_type=account_type, action_date=end_date, trace=False)

        payment = valuation.solve_instalment()

        self.assertAlmostEqual(Decimal(2964.37), Decimal(payment), places=2)
