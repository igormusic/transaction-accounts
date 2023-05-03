from accounts.metadata import *
from accounts.runtime import Calendar


def create_savings_account() -> AccountType:
    acc = AccountType(name="savingsAccount", label="Savings Account")

    current = acc.add_position_type("current", "current balance")
    interest_accrued = acc.add_position_type("accrued", "interest accrued")
    withholding = acc.add_position_type("withholding", "withholding tax")

    acc.add_property_type("monthlyFee", "Monthly Fee", DataType.DECIMAL, True)
    acc.add_property_type("withholdingTax", "Withholding Tax Rate", DataType.DECIMAL, True)

    acc.add_transaction_type("deposit", "Deposit") \
        .add_position_rule(TransactionOperation.CREDIT, current)

    fee_tt = acc.add_transaction_type("fee", "Fee") \
        .add_position_rule(TransactionOperation.DEBIT, current)

    interest_accrued_tt = acc.add_transaction_type("interestAccrued", "Interest Accrued", True) \
        .add_position_rule(TransactionOperation.CREDIT, interest_accrued)

    capitalized_tt = acc.add_transaction_type("capitalized", "Interest Capitalized") \
        .add_position_rule(TransactionOperation.CREDIT, current) \
        .add_position_rule(TransactionOperation.DEBIT, interest_accrued)

    withholding_tt = acc.add_transaction_type("withholdingTax", "Withholding Tax") \
        .add_position_rule(TransactionOperation.CREDIT, withholding)

    accrual_schedule = ScheduleType(name="accrual", label="Accrual Schedule", frequency=ScheduleFrequency.DAILY,
                                    end_type=ScheduleEndType.NO_END,
                                    business_day_adjustment=BusinessDayAdjustment.NO_ADJUSTMENT,
                                    interval_expression="1", start_date_expression="account.start_date")

    acc.add_schedule_type(accrual_schedule)

    compounding_schedule = ScheduleType(name="compounding", label="Compounding Schedule",
                                        frequency=ScheduleFrequency.MONTHLY,
                                        end_type=ScheduleEndType.NO_END,
                                        business_day_adjustment=BusinessDayAdjustment.NO_ADJUSTMENT,
                                        interval_expression="1",
                                        start_date_expression="account.start_date + relativedelta(month=+1) + relativedelta(days=-1)")

    acc.add_schedule_type(compounding_schedule)

    acc.add_scheduled_transaction(compounding_schedule, ScheduledTransactionTiming.END_OF_DAY,
                                  fee_tt,
                                  "account.monthlyFee[value_date]")

    acc.add_scheduled_transaction(accrual_schedule, ScheduledTransactionTiming.END_OF_DAY,
                                  interest_accrued_tt,
                                  "account.current * accountType.interest.get_rate(value_date, account.current) / Decimal(365)")

    acc.add_scheduled_transaction(compounding_schedule, ScheduledTransactionTiming.END_OF_DAY,
                                  capitalized_tt, "account.accrued")

    interest_rate = acc.add_rate_type("interest", "Interest Rate")

    interest_rate.add_tier(date(2019, 1, 1), Decimal(10000), Decimal(0.03))
    interest_rate.add_tier(date(2019, 1, 1), Decimal(100000), Decimal(0.035))
    interest_rate.add_tier(date(2019, 1, 1), Decimal(50000), Decimal(0.04))

    acc.add_trigger_transaction(capitalized_tt, withholding_tt,
                                "transaction.amount * account.withholdingTax[value_date]")

    return acc


def create_loan_given_account() -> AccountType:
    loan_given = AccountType(name="Loan", label="Loan")

    conversion_interest_position = loan_given.add_position_type("conversion_interest", "Conversion Interest")
    early_redemption_fee_position = loan_given.add_position_type("early_redemption_fee", "Early Redemption Fee")
    interest_accrued_position = loan_given.add_position_type("accrued", "Interest Accrued")
    interest_capitalized_position = loan_given.add_position_type("interest_capitalized", "Interest Capitalized")
    principal_position = loan_given.add_position_type("principal", "Principal")

    loan_given.add_date_type(name="accrual_start", label="Accrual Start Date")
    loan_given.add_date_type(name="end_date", label="End Date")

    accrual_schedule = ScheduleType(name="accrual", label="Accrual Schedule", frequency=ScheduleFrequency.DAILY,
                                    end_type=ScheduleEndType.NO_END,
                                    business_day_adjustment=BusinessDayAdjustment.NO_ADJUSTMENT,
                                    interval_expression="1", start_date_expression="account.start_date")

    interest_schedule = ScheduleType(name="interest", label="Interest Schedule", frequency=ScheduleFrequency.MONTHLY,
                                     end_type=ScheduleEndType.NO_END,
                                     business_day_adjustment=BusinessDayAdjustment.NO_ADJUSTMENT,
                                     interval_expression="1", start_date_expression="account.start_date",
                                     end_date_expression="account.end_date",
                                     include_dates_expression="account.end_date")

    redemption_schedule = ScheduleType(name="redemption", label="Redemption Schedule",
                                       frequency=ScheduleFrequency.MONTHLY,
                                       end_type=ScheduleEndType.NO_END,
                                       business_day_adjustment=BusinessDayAdjustment.NO_ADJUSTMENT,
                                       interval_expression="1",
                                       start_date_expression="account.start_date + relativedelta(months=+1)",
                                       end_date_expression="account.end_date",
                                       include_dates_expression="account.end_date")

    advance_schedule = ScheduleType(name="advance", label="Advance Schedule",
                                    frequency=ScheduleFrequency.DAILY,
                                    end_type=ScheduleEndType.END_DATE,
                                    business_day_adjustment=BusinessDayAdjustment.NO_ADJUSTMENT,
                                    interval_expression="1",
                                    start_date_expression="account.start_date",
                                    end_date_expression="account.start_date")

    loan_given.add_schedule_type(accrual_schedule)
    loan_given.add_schedule_type(interest_schedule)
    loan_given.add_schedule_type(redemption_schedule)
    loan_given.add_schedule_type(advance_schedule)

    interest_accrued = loan_given.add_transaction_type("interestAccrued", "Interest Accrued", True) \
        .add_position_rule(TransactionOperation.CREDIT, interest_accrued_position)

    interest_capitalized = loan_given.add_transaction_type("interestCapitalized", "Interest Capitalized") \
        .add_position_rule(TransactionOperation.CREDIT, interest_capitalized_position) \
        .add_position_rule(TransactionOperation.DEBIT, interest_accrued_position) \
        .add_position_rule(TransactionOperation.CREDIT, principal_position)

    early_redemption_fee = loan_given.add_transaction_type("earlyRedemptionFee", "Early Redemption Fee") \
        .add_position_rule(TransactionOperation.CREDIT, early_redemption_fee_position)

    conversion_interest = loan_given.add_transaction_type("conversionInterest", "Conversion Interest") \
        .add_position_rule(TransactionOperation.CREDIT, conversion_interest_position)

    redemption = loan_given.add_transaction_type("redemption", "Redemption") \
        .add_position_rule(TransactionOperation.DEBIT, principal_position)

    advance_transaction = loan_given.add_transaction_type("advance", "Advance") \
        .add_position_rule(TransactionOperation.CREDIT, principal_position)

    additional_advance_transaction = loan_given.add_transaction_type("additionalAdvance", "Additional Advance") \
        .add_position_rule(TransactionOperation.CREDIT, principal_position)

    interest_payment_transaction = loan_given.add_transaction_type("interestPayment", "Interest Payment") \
        .add_position_rule(TransactionOperation.DEBIT, interest_accrued_position)

    loan_given.add_scheduled_transaction(accrual_schedule, ScheduledTransactionTiming.END_OF_DAY,
                                         interest_accrued,
                                         "account.principal * accountType.interest.get_rate(value_date, "
                                         "account.principal) / Decimal(365)")

    loan_given.add_scheduled_transaction(interest_schedule, ScheduledTransactionTiming.END_OF_DAY,
                                         interest_capitalized,
                                         "account.accrued")

    loan_given.add_scheduled_transaction(advance_schedule, ScheduledTransactionTiming.START_OF_DAY,
                                         advance_transaction,
                                         "account.advance")

    loan_given.add_instalment_type(name="payments", label="Payments", timing=ScheduledTransactionTiming.START_OF_DAY,
                                   transaction_type=redemption.name,
                                   property_name="payment",
                                   solve_for_zero_position="principal",
                                   solve_for_date="end_date",
                                   schedule_name=redemption_schedule.name)

    loan_given.add_property_type("advance", "Advance Amount", DataType.DECIMAL, True)
    loan_given.add_property_type("payment", "Payment Amount", DataType.DECIMAL, True)

    interest_rate = loan_given.add_rate_type("interest", "Interest Rate")

    interest_rate.add_tier(date(2000, 1, 1), Decimal(2000000), Decimal(0.0304))
    interest_rate.add_tier(date(2000, 1, 1), Decimal(10000000), Decimal(0.025))
    interest_rate.add_tier(date(2000, 1, 1), Decimal(1E30), Decimal(0.02))

    return loan_given


def get_euro_calendar():
    return Calendar(name="Euro Calendar", is_default=True) \
        .add("GOOD FRIDAY", date(2000, 4, 21)) \
        .add("EASTER MONDAY", date(2000, 4, 24)) \
        .add("LABOUR DAY (01 MAY)", date(2000, 5, 1)) \
        .add("CHRISTMAS DAY (25 DEC)", date(2000, 12, 25)) \
        .add("BOXING DAY (26 DEC)", date(2000, 12, 26)) \
        .add("NEW YEARS DAY (01JAN)", date(2001, 1, 1)) \
        .add("GOOD FRIDAY", date(2001, 4, 13)) \
        .add("EASTER MONDAY", date(2001, 4, 16)) \
        .add("LABOUR DAY (01 MAY)", date(2001, 5, 1)) \
        .add("CHRISTMAS DAY (25 DEC)", date(2001, 12, 25)) \
        .add("BOXING DAY (26 DEC)", date(2001, 12, 26)) \
        .add("NEW YEARS DAY (01JAN)", date(2002, 1, 1)) \
        .add("GOOD FRIDAY", date(2002, 3, 29)) \
        .add("EASTER MONDAY", date(2002, 4, 1)) \
        .add("LABOUR DAY (01 MAY)", date(2002, 5, 1)) \
        .add("CHRISTMAS DAY (25 DEC)", date(2002, 12, 25)) \
        .add("BOXING DAY (26 DEC)", date(2002, 12, 26)) \
        .add("NEW YEARS DAY (01JAN)", date(2003, 1, 1)) \
        .add("GOOD FRIDAY", date(2003, 4, 18)) \
        .add("EASTER MONDAY", date(2003, 4, 21)) \
        .add("LABOUR DAY (01 MAY)", date(2003, 5, 1)) \
        .add("CHRISTMAS DAY (25 DEC)", date(2003, 12, 25)) \
        .add("BOXING DAY (26 DEC)", date(2003, 12, 26)) \
        .add("NEW YEARS DAY (01JAN)", date(2004, 1, 1)) \
        .add("GOOD FRIDAY", date(2004, 4, 9)) \
        .add("EASTER MONDAY", date(2004, 4, 12)) \
        .add("GOOD FRIDAY", date(2005, 3, 25)) \
        .add("EASTER MONDAY", date(2005, 3, 28)) \
        .add("BOXING DAY (26 DEC)", date(2005, 12, 26)) \
        .add("GOOD FRIDAY", date(2006, 4, 14)) \
        .add("EASTER MONDAY", date(2006, 4, 17)) \
        .add("LABOUR DAY (01 MAY)", date(2006, 5, 1)) \
        .add("CHRISTMAS DAY (25 DEC)", date(2006, 12, 25)) \
        .add("BOXING DAY (26 DEC)", date(2006, 12, 26)) \
        .add("NEW YEARS DAY (01JAN)", date(2007, 1, 1)) \
        .add("GOOD FRIDAY", date(2007, 4, 6)) \
        .add("EASTER MONDAY", date(2007, 4, 9)) \
        .add("LABOUR DAY (01 MAY)", date(2007, 5, 1)) \
        .add("CHRISTMAS DAY (25 DEC)", date(2007, 12, 25)) \
        .add("BOXING DAY (26 DEC)", date(2007, 12, 26)) \
        .add("NEW YEARS DAY (01JAN)", date(2008, 1, 1)) \
        .add("GOOD FRIDAY", date(2008, 3, 21)) \
        .add("EASTER MONDAY", date(2008, 3, 24)) \
        .add("LABOUR DAY (01 MAY)", date(2008, 5, 1)) \
        .add("CHRISTMAS DAY (25 DEC)", date(2008, 12, 25)) \
        .add("BOXING DAY (26 DEC)", date(2008, 12, 26)) \
        .add("NEW YEARS DAY (01JAN)", date(2009, 1, 1)) \
        .add("GOOD FRIDAY", date(2009, 4, 10)) \
        .add("EASTER MONDAY", date(2009, 4, 13)) \
        .add("LABOUR DAY (01 MAY)", date(2009, 5, 1)) \
        .add("CHRISTMAS DAY (25 DEC)", date(2009, 12, 25)) \
        .add("NEW YEARS DAY (01JAN)", date(2010, 1, 1)) \
        .add("GOOD FRIDAY", date(2010, 4, 2)) \
        .add("EASTER MONDAY", date(2010, 4, 5)) \
        .add("GOOD FRIDAY", date(2011, 4, 22)) \
        .add("EASTER MONDAY", date(2011, 4, 25)) \
        .add("BOXING DAY (26 DEC)", date(2011, 12, 26)) \
        .add("GOOD FRIDAY", date(2012, 4, 6)) \
        .add("EASTER MONDAY", date(2012, 4, 9)) \
        .add("LABOUR DAY (01 MAY)", date(2012, 5, 1)) \
        .add("CHRISTMAS DAY (25 DEC)", date(2012, 12, 25)) \
        .add("BOXING DAY (26 DEC)", date(2012, 12, 26)) \
        .add("NEW YEARS DAY (01JAN)", date(2013, 1, 1)) \
        .add("GOOD FRIDAY", date(2013, 3, 29)) \
        .add("EASTER MONDAY", date(2013, 4, 1)) \
        .add("LABOUR DAY (01 MAY)", date(2013, 5, 1)) \
        .add("CHRISTMAS DAY (25 DEC)", date(2013, 12, 25)) \
        .add("BOXING DAY (26 DEC)", date(2013, 12, 26)) \
        .add("NEW YEARS DAY (01JAN)", date(2014, 1, 1)) \
        .add("GOOD FRIDAY", date(2014, 4, 18)) \
        .add("EASTER MONDAY", date(2014, 4, 21)) \
        .add("LABOUR DAY (01 MAY)", date(2014, 5, 1)) \
        .add("CHRISTMAS DAY (25 DEC)", date(2014, 12, 25)) \
        .add("BOXING DAY (26 DEC)", date(2014, 12, 26)) \
        .add("NEW YEARS DAY (01JAN)", date(2015, 1, 1)) \
        .add("GOOD FRIDAY", date(2015, 4, 3)) \
        .add("EASTER MONDAY", date(2015, 4, 6)) \
        .add("LABOUR DAY (01 MAY)", date(2015, 5, 1)) \
        .add("CHRISTMAS DAY (25 DEC)", date(2015, 12, 25)) \
        .add("NEW YEARS DAY (01JAN)", date(2016, 1, 1)) \
        .add("GOOD FRIDAY", date(2016, 3, 25)) \
        .add("EASTER MONDAY", date(2016, 3, 28)) \
        .add("BOXING DAY (26 DEC)", date(2016, 12, 26)) \
        .add("GOOD FRIDAY", date(2017, 4, 14)) \
        .add("EASTER MONDAY", date(2017, 4, 17)) \
        .add("LABOUR DAY (01 MAY)", date(2017, 5, 1)) \
        .add("CHRISTMAS DAY (25 DEC)", date(2017, 12, 25)) \
        .add("BOXING DAY (26 DEC)", date(2017, 12, 26)) \
        .add("NEW YEARS DAY (01JAN)", date(2018, 1, 1)) \
        .add("GOOD FRIDAY", date(2018, 3, 30)) \
        .add("EASTER MONDAY", date(2018, 4, 2)) \
        .add("LABOUR DAY (01 MAY)", date(2018, 5, 1)) \
        .add("CHRISTMAS DAY (25 DEC)", date(2018, 12, 25)) \
        .add("BOXING DAY (26 DEC)", date(2018, 12, 26)) \
        .add("NEW YEARS DAY (01JAN)", date(2019, 1, 1)) \
        .add("GOOD FRIDAY", date(2019, 4, 19)) \
        .add("EASTER MONDAY", date(2019, 4, 22)) \
        .add("LABOUR DAY (01 MAY)", date(2019, 5, 1)) \
        .add("CHRISTMAS DAY (25 DEC)", date(2019, 12, 25)) \
        .add("BOXING DAY (26 DEC)", date(2019, 12, 26)) \
        .add("NEW YEARS DAY (01JAN)", date(2020, 1, 1)) \
        .add("GOOD FRIDAY", date(2020, 4, 10)) \
        .add("EASTER MONDAY", date(2020, 4, 13)) \
        .add("LABOUR DAY (01 MAY)", date(2020, 5, 1)) \
        .add("CHRISTMAS DAY (25 DEC)", date(2020, 12, 25)) \
        .add("NEW YEARS DAY (01JAN)", date(2021, 1, 1)) \
        .add("GOOD FRIDAY", date(2021, 4, 2)) \
        .add("EASTER MONDAY", date(2021, 4, 5)) \
        .add("GOOD FRIDAY", date(2022, 4, 15)) \
        .add("EASTER MONDAY", date(2022, 4, 18)) \
        .add("BOXING DAY (26 DEC)", date(2022, 12, 26)) \
        .add("GOOD FRIDAY", date(2023, 4, 7)) \
        .add("EASTER MONDAY", date(2023, 4, 10)) \
        .add("LABOUR DAY (01 MAY)", date(2023, 5, 1)) \
        .add("CHRISTMAS DAY (25 DEC)", date(2023, 12, 25)) \
        .add("BOXING DAY (26 DEC)", date(2023, 12, 26)) \
        .add("NEW YEARS DAY (01JAN)", date(2024, 1, 1)) \
        .add("GOOD FRIDAY", date(2024, 3, 29)) \
        .add("EASTER MONDAY", date(2024, 4, 1)) \
        .add("LABOUR DAY (01 MAY)", date(2024, 5, 1)) \
        .add("CHRISTMAS DAY (25 DEC)", date(2024, 12, 25)) \
        .add("BOXING DAY (26 DEC)", date(2024, 12, 26)) \
        .add("NEW YEARS DAY (01JAN)", date(2025, 1, 1)) \
        .add("GOOD FRIDAY", date(2025, 4, 18)) \
        .add("EASTER MONDAY", date(2025, 4, 21)) \
        .add("LABOUR DAY (01 MAY)", date(2025, 5, 1)) \
        .add("CHRISTMAS DAY (25 DEC)", date(2025, 12, 25)) \
        .add("BOXING DAY (26 DEC)", date(2025, 12, 26)) \
        .add("NEW YEARS DAY (01JAN)", date(2026, 1, 1)) \
        .add("GOOD FRIDAY", date(2026, 4, 3)) \
        .add("EASTER MONDAY", date(2026, 4, 6)) \
        .add("LABOUR DAY (01 MAY)", date(2026, 5, 1)) \
        .add("CHRISTMAS DAY (25 DEC)", date(2026, 12, 25)) \
        .add("NEW YEARS DAY (01JAN)", date(2027, 1, 1)) \
        .add("GOOD FRIDAY", date(2027, 3, 26)) \
        .add("EASTER MONDAY", date(2027, 3, 29)) \
        .add("GOOD FRIDAY", date(2028, 4, 14)) \
        .add("EASTER MONDAY", date(2028, 4, 17)) \
        .add("LABOUR DAY (01 MAY)", date(2028, 5, 1)) \
        .add("CHRISTMAS DAY (25 DEC)", date(2028, 12, 25)) \
        .add("BOXING DAY (26 DEC)", date(2028, 12, 26)) \
        .add("NEW YEARS DAY (01JAN)", date(2029, 1, 1)) \
        .add("GOOD FRIDAY", date(2029, 3, 30)) \
        .add("EASTER MONDAY", date(2029, 4, 2)) \
        .add("LABOUR DAY (01 MAY)", date(2029, 5, 1)) \
        .add("CHRISTMAS DAY (25 DEC)", date(2029, 12, 25)) \
        .add("BOXING DAY (26 DEC)", date(2029, 12, 26)) \
        .add("NEW YEARS DAY (1 JAN)", date(2030, 1, 1)) \
        .add("GOOD FRIDAY", date(2030, 4, 19)) \
        .add("EASTER MONDAY", date(2030, 4, 22)) \
        .add("LABOUR DAY", date(2030, 5, 1)) \
        .add("CHRISTMAS DAY (25 DEC)", date(2030, 12, 25)) \
        .add("BOXING DAY (26 DEC)", date(2030, 12, 26))
