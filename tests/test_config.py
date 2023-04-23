from accounts.metadata import *


def create_savings_account() -> AccountType:
    acc = AccountType(name="savingsAccount", label="Savings Account")

    current = acc.add_position_type("current", "current balance")
    interest_accrued = acc.add_position_type("accrued", "interest accrued")
    withholding = acc.add_position_type("withholding", "withholding tax")

    acc.add_transaction_type("deposit", "Deposit")\
        .add_position_rule(TransactionOperation.CREDIT, current)

    interest_accrued_tt = acc.add_transaction_type("interestAccrued", "Interest Accrued") \
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

    acc.add_scheduled_transaction(accrual_schedule, ScheduledTransactionTiming.END_OF_DAY,
                                  interest_accrued_tt,
                                  "account.current * accountType.interest.get_rate(account.current) / Decimal(365)")

    acc.add_scheduled_transaction(compounding_schedule, ScheduledTransactionTiming.END_OF_DAY,
                                  capitalized_tt, "account.accrued")

    interest_rate = acc.add_rate_type("interest", "Interest Rate")

    interest_rate.add_tier(Decimal(10000), Decimal(0.03))
    interest_rate.add_tier(Decimal(100000), Decimal(0.035))
    interest_rate.add_tier(Decimal(50000), Decimal(0.04))

    acc.add_trigger_transaction(capitalized_tt, withholding_tt, "transaction.amount * Decimal(0.2)")

    return acc
