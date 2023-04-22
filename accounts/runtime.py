from datetime import timedelta
from typing import Mapping, Any

from dateutil.relativedelta import *

from accounts.metadata import *


class Position:
    def __init__(self):
        self.amount = Decimal(0)

    def apply_operation(self, operation: TransactionOperation, amount: Decimal):
        if operation == TransactionOperation.CREDIT:
            self.amount = self.amount + amount
        elif operation == TransactionOperation.DEBIT:
            self.amount = self.amount - amount
        else:  # Replace
            self.amount = amount

    def copy(self):
        position = Position()
        position.amount = self.amount
        return position


class Transaction:
    amount = Decimal(0)

    def __init__(self, action_date: date, value_date: date, transaction_type: str, amount: Decimal,
                 system_generated: bool):
        self.action_date = action_date
        self.value_date = value_date
        self.transaction_type = transaction_type
        self.amount = amount
        self.system_generated = system_generated

    def display(self):
        print("actionDate = {0}, valueDate = {1}, transactionType = {2}, amount = {3}, system_generated = {4}".format(
            self.action_date,
            self.value_date,
            self.transaction_type,
            self.amount,
            self.system_generated))


class Schedule:
    def __init__(self, start_date: date, end_type: ScheduleEndType, frequency: ScheduleFrequency, interval: int = 0,
                 adjustment: BusinessDayAdjustment = BusinessDayAdjustment.NO_ADJUSTMENT,
                 end_date: date = None, number_of_repeats: int = 0):
        self.start_date = start_date
        self.end_type = end_type
        self.interval = interval
        self.frequency = frequency
        self.adjustment = adjustment
        self.end_date = end_date
        self.number_of_repeats = number_of_repeats
        self.include_dates: list[date] = []
        self.exclude_dates: list[date] = []
        self.cached_dates: dict[date, list[date]] = {}

    def __is_simple_daily_schedule(self):
        return (self.frequency == ScheduleFrequency.DAILY and
                self.interval == 1 and
                self.adjustment == BusinessDayAdjustment.NO_ADJUSTMENT)

    def __last_date(self):
        return self.start_date + relativedelta(years=+50)

    def is_due(self, test_date: date) -> bool:
        if self.__is_simple_daily_schedule():
            if self.end_type == ScheduleEndType.NO_END:
                return test_date >= self.start_date
            elif self.end_type == ScheduleEndType.END_DATE:
                return self.start_date <= test_date <= self.end_date

        dates: list[test_date] = self.get_all_dates(self.__last_date())

        return test_date in dates

    def get_all_dates(self, to_date: date):
        if self.cached_dates and to_date in self.cached_dates:
            return self.cached_dates[to_date]

        dates: list[date] = []
        repeats: int = 1
        iterator: date = self.start_date
        adjusted_date = self.__get_adjusted(iterator)

        while not self.__is_completed(repeats, adjusted_date, to_date):
            dates.append(adjusted_date)

            iterator = self.__next(repeats)
            adjusted_date = self.__get_adjusted(iterator)
            repeats += 1

        dates.extend(include_date for include_date in self.include_dates if include_date not in dates)

        dates = [keep_date for keep_date in dates if keep_date not in self.exclude_dates]

        dates.sort()

        self.cached_dates[to_date] = dates

        return dates

    def __next(self, repeats: int) -> date:
        if self.frequency == ScheduleFrequency.DAILY:
            return self.start_date + relativedelta(days=+ self.interval * repeats)

        return self.start_date + relativedelta(months=+ self.interval * repeats)

    def __is_completed(self, repeats: int, test_date: date, last_date: date) -> bool:
        if test_date > last_date:
            return True
        elif self.end_type == ScheduleEndType.END_DATE and test_date > self.end_date:
            return True
        elif self.end_type == ScheduleEndType.NO_END:
            return False

        return (self.end_type == ScheduleEndType.END_REPEATS and
                repeats > self.number_of_repeats)

    def __get_adjusted(self, test_date: date):
        if self.adjustment == BusinessDayAdjustment.NO_ADJUSTMENT:
            return test_date

        # TODO add calendar and call get_adjusted()
        return test_date


class ExternalTransaction:
    def __init__(self, transaction_type_name: str, amount: Decimal, value_date: date):
        self.transaction_type_name = transaction_type_name
        self.amount = amount
        self.value_date = value_date


class Account:
    def __init__(self, start_date: date, account_type: AccountType, config: Configuration):
        self.start_date = start_date
        self.account_type_name: str = account_type.name
        self.config_version: str = config.version
        self.positions: dict[str, Position] = {}
        self.schedules: dict[str, Schedule] = {}
        self.transactions: list[Transaction] = []

        self.__initialize_positions(account_type, config)
        self.__initialize_schedules(account_type, config)

    def __initialize_schedules(self, account_type: AccountType, config: Configuration):
        for schedule_type in account_type.schedule_types:
            schedule = Schedule(self.evaluate(schedule_type.start_date_expression, {"config": config, "account": self}),
                                schedule_type.end_type,
                                schedule_type.frequency,
                                self.evaluate(schedule_type.interval_expression, {"config": config, "account": self}),
                                schedule_type.business_day_adjustment)

            if schedule_type.end_date_expression:
                schedule.end_date = self.evaluate(schedule_type.end_date_expression,
                                                  {"config": config, "account": self})

            if schedule_type.number_of_repeats_expression:
                schedule.number_of_repeats = self.evaluate(schedule_type.number_of_repeats_expression)

            self.schedules[schedule_type.name] = schedule

    def __initialize_positions(self, account_type, config):
        for transaction_type_name in account_type.transaction_type_names:
            transaction_type = config.get_transaction_type(transaction_type_name)
            for rule in transaction_type.position_rules:
                if rule.position_type_name not in self.positions:
                    self.positions[rule.position_type_name] = Position()

    def add_transaction(self, transaction: Transaction, transaction_type: TransactionType) -> Transaction:
        for rule in transaction_type.position_rules:
            position = self.positions[rule.position_type_name]
            position.apply_operation(rule.operation, transaction.amount)

        self.transactions.append(transaction)

    def evaluate(self, expression: str, locals: Optional[Mapping[str, Any]]) -> Any:
        try:
            value = eval(expression, None, locals)
        except Exception as e:
            raise ValueError(f'Error evaluating expression: {expression} {e.args}') from e
        else:
            return value

    def __getattr__(self, method_name):
        if method_name in self.positions:
            return self.positions[method_name].amount
        else:
            raise AttributeError(f'No such attribute: {method_name}')


def group_by_date(external_transactions):
    grouped = {}

    for external_transaction in external_transactions:
        if external_transaction.value_date not in grouped:
            grouped[external_transaction.value_date] = [external_transaction]
        else:
            grouped[external_transaction.value_date].append(external_transaction)

    return grouped


class AccountValuation:
    def __init__(self, account: Account, account_type: AccountType, configuration: Configuration, action_date: date):
        self.account = account
        self.account_type = account_type
        self.configuration = configuration
        self.action_date = action_date

    def forecast(self, to_value_date: date, external_transactions):
        value_date = self.account.start_date

        self.start_of_day(value_date)
        self.process_external_transactions(value_date, external_transactions)

        while value_date < to_value_date:
            self.end_of_day(value_date)

            value_date = value_date + timedelta(days=1)

            self.start_of_day(value_date)
            self.process_external_transactions(value_date, external_transactions)

    def process_external_transactions(self, value_date: date, external_transactions):
        if value_date in external_transactions:
            for external_transaction in external_transactions[value_date]:
                transaction_type = self.configuration.get_transaction_type(external_transaction.transaction_type_name)
                self.__create_transaction(transaction_type, value_date, external_transaction.amount, False)

    def start_of_day(self, value_date):
        for scheduled_transaction in self.account_type.scheduled_transactions:
            if scheduled_transaction.timing == ScheduledTransactionTiming.START_OF_DAY:
                self.__create_transaction_if_due(value_date, scheduled_transaction)

    def __create_transaction_if_due(self, value_date: date, scheduled_transaction: ScheduledTransaction):
        schedule = self.account.schedules[scheduled_transaction.schedule_name]

        if schedule.is_due(value_date):
            transaction_type = self.configuration.get_transaction_type(scheduled_transaction.generated_transaction_type)

            self.__create_calculated_transaction(value_date, transaction_type, scheduled_transaction.amount_expression)

    def __create_calculated_transaction(self, value_date: date, transaction_type: TransactionType,
                                        amount_expression: str):
        try:
            amount = self.account.evaluate(amount_expression, {"config": self.configuration, "account": self.account})
        except Exception as e:

            raise Exception(f'Error evaluating expression: {amount_expression} {e.args}') from e
        else:
            if amount != Decimal(0):
                self.__create_transaction(transaction_type, value_date, amount, True)

    def __create_transaction(self, transaction_type: TransactionType, value_date: date,
                             amount: Decimal, system_generated: bool):
        transaction = Transaction(self.action_date, value_date, transaction_type.name, amount, system_generated)
        self.account.add_transaction(transaction, transaction_type)

        triggered_transaction = self.configuration.get_trigger_transaction(transaction_type.name)

        if triggered_transaction:
            trigger_amount = self.account.evaluate(triggered_transaction.amount_expression,
                                                   {"transaction": transaction,
                                                    "config": self.configuration,
                                                    "account": self.account})
            generated_transaction_type = self.configuration \
                .get_transaction_type(triggered_transaction.generated_transaction_type)
            self.__create_transaction(generated_transaction_type, value_date, trigger_amount, True)

    def end_of_day(self, value_date):
        for scheduled_transaction in self.account_type.scheduled_transactions:
            if scheduled_transaction.timing == ScheduledTransactionTiming.END_OF_DAY:
                self.__create_transaction_if_due(value_date, scheduled_transaction)
