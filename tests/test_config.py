from accounts.metadata import *


def create_savings_account() -> Configuration:
    config: Configuration = Configuration(version="v1")

    current = config.add_position_type("current", "current balance")
    interest_accrued = config.add_position_type("accrued", "interest accrued")
    withholding = config.add_position_type("withholding", "withholding tax")

    deposit = config.add_transaction_type("deposit", "Deposit").add_position_rule(TransactionOperation.CREDIT, current)

    interest_accrued_tt = config.add_transaction_type("interestAccrued", "Interest Accrued")
    interest_accrued_tt.add_position_rule(TransactionOperation.CREDIT, interest_accrued)

    capitalized = config.add_transaction_type("capitalized", "Interest Capitalized").add_position_rule(
        TransactionOperation.CREDIT, current).add_position_rule(TransactionOperation.DEBIT, interest_accrued)

    withholding_txn = config.add_transaction_type("withholdingTax", "Withholding Tax").add_position_rule(
        TransactionOperation.CREDIT, withholding)

    savings_account = config.add_account_type("savingsAccount", "Savings Account")

    savings_account.add_transaction_type(deposit)
    savings_account.add_transaction_type(interest_accrued_tt)
    savings_account.add_transaction_type(capitalized)
    savings_account.add_transaction_type(withholding_txn)

    accrual_schedule = ScheduleType(name="accrual", label="Accrual Schedule", frequency=ScheduleFrequency.DAILY,
                                    end_type=ScheduleEndType.NO_END,
                                    business_day_adjustment=BusinessDayAdjustment.NO_ADJUSTMENT,
                                    interval_expression="1", start_date_expression="account.start_date")

    savings_account.add_schedule_type(accrual_schedule)

    compounding_schedule = ScheduleType(name="compounding", label="Compounding Schedule", frequency=ScheduleFrequency.MONTHLY,
                                        end_type=ScheduleEndType.NO_END,
                                        business_day_adjustment=BusinessDayAdjustment.NO_ADJUSTMENT,
                                        interval_expression="1",
                                        start_date_expression="account.start_date + relativedelta(month=+1) + relativedelta(days=-1)")

    savings_account.add_schedule_type(compounding_schedule)

    savings_account.add_scheduled_transaction(accrual_schedule, ScheduledTransactionTiming.END_OF_DAY,
                                              interest_accrued_tt,
                                              "account.current * config.interest.get_rate(account.current) / Decimal(365)")

    savings_account.add_scheduled_transaction(compounding_schedule, ScheduledTransactionTiming.END_OF_DAY,
                                              capitalized, "account.accrued")

    interest_rate = config.add_rate_type("interest", "Interest Rate")

    interest_rate.add_tier(Decimal(10000), Decimal(0.03))
    interest_rate.add_tier(Decimal(100000), Decimal(0.035))
    interest_rate.add_tier(Decimal(50000), Decimal(0.04))

    config.add_trigger_transaction(capitalized, withholding_txn, "transaction.amount * Decimal(0.2)")

    return config
