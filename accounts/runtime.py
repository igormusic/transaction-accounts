from datetime import timedelta
from itertools import groupby
from typing import Mapping, Any
from dateutil.relativedelta import *
from pydantic import Field

from accounts.metadata import *
import scipy.optimize


class Position(BaseModel):
    amount: Decimal = Decimal(0)

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


class Transaction(BaseModel):
    amount = Decimal(0)
    action_date: date
    value_date: date
    transaction_type: str
    amount: Decimal
    system_generated: bool

    def to_external_transaction(self):
        return ExternalTransaction(
            transaction_type_name=self.transaction_type,
            amount=self.amount,
            value_date=self.value_date
        )


class Schedule(BaseModel):
    start_date: date
    end_type: ScheduleEndType
    frequency: ScheduleFrequency
    interval: int = 0,
    adjustment: BusinessDayAdjustment = BusinessDayAdjustment.NO_ADJUSTMENT
    end_date: Optional[date]
    number_of_repeats: int = 0
    include_dates: list[date] = []
    exclude_dates: list[date] = []
    cached_dates: dict[date, date] = Field(default_factory=dict, exclude=True)

    class Config:
        # exclude the "cached_dates" field from JSON serialization
        exclude = {"cached_dates"}

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

        if not self.cached_dates:
            # create dictionary of dates for each date
            self.cached_dates = {date: date for date in self.get_all_dates(self.__last_date())}

        # check if test_date is in dictionary
        return test_date in self.cached_dates

    def get_all_dates(self, to_date: date):
        if self.cached_dates:
            return self.cached_dates.keys()

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

        self.cached_dates = {iter: iter for iter in dates}

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


class ExternalTransaction(BaseModel):
    transaction_type_name: str
    amount: Decimal
    value_date: date


class PropertyValue(BaseModel):
    value: Dict[date, Any] = {}

    def __getitem__(self, value_date: date):
        # find first date that is less than or equal to value_date
        index_date = max([d for d in self.value.keys() if d <= value_date])
        return self.value[index_date]

    def __setitem__(self, value_date: date, value):
        self.value[value_date] = value


class Instalment(BaseModel):
    amount: Decimal
    is_fixed: bool


class Account(BaseModel):
    start_date: date
    account_type_name: str
    positions: dict[str, Position] = {}
    value_dated_properties: dict[str, PropertyValue] = {}
    properties: dict[str, Any] = {}
    dates: dict[str, date] = {}
    schedules: dict[str, Schedule] = {}
    transactions: list[Transaction] = []
    instalments: dict[str, Instalment] = {}

    def __init__(self, **kw):
        super().__init__(**kw)
        if "account_type" in kw:
            account_type: AccountType = kw["account_type"]
            self.__validate_properties(account_type)
            self.__initialize_positions(account_type)
            self.__initialize_schedules(account_type)
            self.__initialize_instalment(account_type)

    def __validate_properties(self, account_type: AccountType):
        for property_type in account_type.property_types:
            if property_type.value_dated:
                if property_type.name not in self.value_dated_properties:
                    raise ValueError(
                        f"Value dated property {property_type.name} is required for account type {account_type.name}")
            else:
                if property_type.name not in self.properties:
                    raise ValueError(f"Property {property_type.name} is required for account type {account_type.name}")

    def __initialize_schedules(self, account_type: AccountType):
        for schedule_type in account_type.schedule_types:
            # skip if schedule already exists
            if schedule_type.name in self.schedules:
                continue

            schedule = Schedule(
                start_date=self.evaluate(schedule_type.start_date_expression,
                                         {"accountType": account_type, "account": self,
                                          "value_date": self.start_date}),
                end_type=schedule_type.end_type,
                frequency=schedule_type.frequency,
                interval=self.evaluate(schedule_type.interval_expression, {"accountType": account_type,
                                                                           "account": self,
                                                                           "value_date": self.start_date}),
                adjustment=schedule_type.business_day_adjustment)

            if schedule_type.end_date_expression:
                schedule.end_date = self.evaluate(schedule_type.end_date_expression,
                                                  {"accountType": account_type,
                                                   "account": self,
                                                   "value_date": self.start_date})

            if schedule_type.number_of_repeats_expression:
                schedule.number_of_repeats = self.evaluate(schedule_type.number_of_repeats_expression)

            self.schedules[schedule_type.name] = schedule

    def __initialize_positions(self, account_type: AccountType):
        for transaction_type in account_type.transaction_types:
            for rule in transaction_type.position_rules:
                if rule.position_type_name not in self.positions:
                    self.positions[rule.position_type_name] = Position()

    def __initialize_instalment(self, account_type: AccountType):
        instalment_type = account_type.instalment_type

        # if no instalments create default one
        if instalment_type and len(self.instalments.items()) == 0:
            for date_value in self.schedules[instalment_type.schedule_name].get_all_dates(
                    self.start_date + relativedelta(years=+50)):
                self.instalments[date_value.strftime("%Y-%m-%d")] = Instalment(amount=Decimal(0), is_fixed=False)

    def apply_calculated_installment(self, amount: Decimal):
        # set all instalments to calculated amount if fixed is false
        for instalment in self.instalments.values():
            if not instalment.is_fixed:
                instalment.amount = amount

    def add_transaction(self, transaction: Transaction, transaction_type: TransactionType) -> dict[str, Decimal]:
        updated_positions: dict[str, Decimal] = {}
        for rule in transaction_type.position_rules:
            position = self.positions[rule.position_type_name]
            position.apply_operation(rule.operation, transaction.amount)
            updated_positions[rule.position_type_name] = position.amount

        self.transactions.append(transaction)

        return updated_positions

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
        if method_name in self.properties:
            return self.properties[method_name]
        if method_name in self.dates:
            return self.dates[method_name]
        else:
            raise AttributeError(f'No such attribute: {method_name}')

    class Config:
        exclude = {"config"}


def group_by_date(external_transactions: List[ExternalTransaction]) -> Dict[date, List[ExternalTransaction]]:
    keyfunc = lambda x: x.value_date

    groups = groupby(sorted(external_transactions, key=keyfunc), keyfunc)  # Sort the list by the keys and group by them

    return {key: list(group) for key, group in groups}


class TransactionDifference(BaseModel):
    amount = Decimal(0)
    value_date: date
    transaction_type: str
    amount: Decimal
    original: List[Transaction] = []
    new: List[Transaction] = []


def valuation_difference(original: List[Transaction], new: List[Transaction]) -> Dict[
    date, list[TransactionDifference]]:
    keyfunc = lambda x: (x.value_date, x.transaction_type)

    original_grouped = {key: list(group)
                        for key, group
                        in groupby(
            sorted(original, key=keyfunc), keyfunc)}

    new_grouped = {key: list(group)
                   for key, group
                   in groupby(
            sorted(new, key=keyfunc), keyfunc)}

    difference_list = list(get_difference(new_grouped, original_grouped))

    return {key: list(group)
            for key, group
            in groupby(
            sorted(difference_list, key=lambda x: x.value_date),
            lambda x: x.value_date)}


def get_difference(new_grouped, original_grouped):
    # Well done Chat GPT 4!
    for value_date, transaction_type in set(original_grouped.keys()).union(set(new_grouped.keys())):
        original_transactions = original_grouped.get((value_date, transaction_type), [])
        new_transactions = new_grouped.get((value_date, transaction_type), [])

        original_amount = sum([t.amount for t in original_transactions])
        new_amount = sum([t.amount for t in new_transactions])

        if original_amount != new_amount:
            yield TransactionDifference(
                value_date=value_date,
                transaction_type=transaction_type,
                amount=new_amount - original_amount,
                original=original_transactions,
                new=new_transactions)


class TransactionTrace(BaseModel):
    transaction: Transaction
    positions: Dict[str, Decimal]

    def __str__(self):
        return f" {self.transaction.value_date} {self.transaction.transaction_type} {self.transaction.amount} {self.positions}"


class AccountValuation(BaseModel):
    account: Account
    account_type: AccountType
    action_date: date
    trace: bool = False
    trace_list: List[TransactionTrace] = []

    def init_account(self):
        # reset all positions to zero
        for position in self.account.positions.values():
            position.amount = Decimal(0)

        self.account.transactions = []

        self.trace_list = []

    def forecast(self, to_value_date: date, external_transactions: dict[date, List[ExternalTransaction]]):
        value_date = self.account.start_date

        self.start_of_day(value_date)
        self.process_external_transactions(value_date, external_transactions)

        while value_date < to_value_date:
            self.end_of_day(value_date)

            value_date = value_date + timedelta(days=1)

            self.start_of_day(value_date)
            self.process_external_transactions(value_date, external_transactions)

    def process_external_transactions(self, value_date: date,
                                      external_transactions: dict[date, List[ExternalTransaction]]):
        if value_date in external_transactions:
            for external_transaction in external_transactions[value_date]:
                transaction_type = self.account_type.get_transaction_type(external_transaction.transaction_type_name)
                self.__create_transaction(transaction_type, value_date, external_transaction.amount, False)

    def start_of_day(self, value_date):
        for scheduled_transaction in self.account_type.scheduled_transactions:
            if scheduled_transaction.timing == ScheduledTransactionTiming.START_OF_DAY:
                self.__create_transaction_if_due(value_date, scheduled_transaction)

        value_date_str = value_date.strftime('%Y-%m-%d')

        if self.account_type.instalment_type:
            if self.account_type.instalment_type.timing == ScheduledTransactionTiming.START_OF_DAY \
                    and value_date_str in self.account.instalments:
                instalment = self.account.instalments[value_date_str]
                transaction_type = self.account_type.get_transaction_type(
                    self.account_type.instalment_type.transaction_type)
                self.__create_transaction(transaction_type, value_date, instalment.amount, True)

    def __create_transaction_if_due(self, value_date: date, scheduled_transaction: ScheduledTransaction):
        schedule = self.account.schedules[scheduled_transaction.schedule_name]

        if schedule.is_due(value_date):
            transaction_type = self.account_type.get_transaction_type(scheduled_transaction.generated_transaction_type)

            self.__create_calculated_transaction(value_date, transaction_type, scheduled_transaction.amount_expression)

    def __create_calculated_transaction(self, value_date: date, transaction_type: TransactionType,
                                        amount_expression: str):
        try:
            amount = self.account.evaluate(amount_expression,
                                           {"accountType": self.account_type,
                                            "account": self.account,
                                            "value_date": value_date})

            if not transaction_type.maximum_precision:
                amount = Decimal(round(amount, 2))

        except Exception as e:
            raise Exception(
                f'Error calculating {transaction_type.name} on {value_date} expression : {amount_expression} {e.args}') from e
        else:
            if amount != Decimal(0):
                self.__create_transaction(transaction_type, value_date, amount, True)

    def __create_transaction(self, transaction_type: TransactionType, value_date: date,
                             amount: Decimal, system_generated: bool):

        transaction = Transaction(action_date=self.action_date, value_date=value_date,
                                  transaction_type=transaction_type.name,
                                  amount=amount, system_generated=system_generated)

        positions = self.account.add_transaction(transaction, transaction_type)

        if self.trace:
            self.trace_list.append(TransactionTrace(transaction=transaction, positions=positions))

        triggered_transaction = self.account_type.get_trigger_transaction(transaction_type.name)

        if triggered_transaction:
            trigger_amount = self.account.evaluate(triggered_transaction.amount_expression,
                                                   {"transaction": transaction,
                                                    "accountType": self.account_type,
                                                    "account": self.account,
                                                    "value_date": value_date})

            generated_transaction_type = self.account_type.get_transaction_type(
                triggered_transaction.generated_transaction_type)
            self.__create_transaction(generated_transaction_type, value_date, trigger_amount, True)

    def end_of_day(self, value_date):
        for scheduled_transaction in self.account_type.scheduled_transactions:
            if scheduled_transaction.timing == ScheduledTransactionTiming.END_OF_DAY:
                self.__create_transaction_if_due(value_date, scheduled_transaction)

    def __calculate_for_instalment(self, value: Decimal) -> Decimal:
        self.init_account()

        self.account.apply_calculated_installment(value)
        self.forecast(self.account.dates[self.account_type.instalment_type.solve_for_date], {})
        result = self.account.positions[self.account_type.instalment_type.solve_for_zero_position].amount
        print(f'instalment {value} -> {self.account_type.instalment_type.solve_for_zero_position} {result}')
        return result

    def solve_instalment(self) -> Decimal:
        amount = scipy.optimize.brentq(self.__calculate_for_instalment, Decimal(-100000000), Decimal(100000000),
                                       xtol=Decimal(0.01))

        amount = Decimal(round(amount, 2))
        # apply amount to instalments
        self.account.apply_calculated_installment(amount)

        return amount


class Solver:
    valuer: AccountValuation

    def __init__(self, valuer: AccountValuation):
        self.valuer = valuer


class HolidayDate(BaseModel):
    description: str
    value: date


class BusinessDayCalculation(Enum):
    ANY_DAY = "AnyDay"
    PREVIOUS_BUSINESS_DAY = "PreviousBusinessDay"
    NEXT_BUSINESS_DAY = "NextBusinessDay"
    CLOSEST_BUSINESS_DAY_OR_NEXT = "ClosestBusinessDayOrNext"
    NEXT_BUSINESS_DAY_THIS_MONTH_OR_PREVIOUS = "NextBusinessDayThisMonthOrPrevious"


class Calendar(BaseModel):
    name: str
    is_default: bool
    holidays: List[HolidayDate] = []
    holidays_map: Dict[date, HolidayDate] = None

    def add(self, description: str, value: date) -> 'Calendar':
        self.holidays.append(HolidayDate(description=description, value=value))
        return self

    def __holidays_map(self):
        if self.holidays_map is None:
            self.holidays_map = {holiday.value: holiday for holiday in self.holidays}

        return self.holidays_map

    def is_business_day(self, value: date):
        if value.weekday() == 5 or value.weekday() == 6:
            return False

        return value not in self.__holidays_map()

    def get_calculated_business_day(self, value: date, adjustment: BusinessDayCalculation):
        if adjustment == BusinessDayCalculation.ANY_DAY:
            return value

        if adjustment == BusinessDayCalculation.PREVIOUS_BUSINESS_DAY:
            return self.get_previous_business_day(value)

        if adjustment == BusinessDayCalculation.NEXT_BUSINESS_DAY:
            return self.get_next_business_day(value)

        previous_business_day = self.get_previous_business_day(value)
        next_business_day = self.get_next_business_day(value)

        if adjustment == BusinessDayCalculation.CLOSEST_BUSINESS_DAY_OR_NEXT:
            if (value - previous_business_day).days > (next_business_day - value).days:
                return next_business_day
            elif (value - previous_business_day).days < (next_business_day - value).days:
                return previous_business_day
            else:
                return next_business_day

        # last option is NextBusinessDayThisMonthOrPrevious

        if next_business_day.month == value.month:
            return next_business_day

        return previous_business_day

    def get_previous_business_day(self, date: date):
        while not self.is_business_day(date):
            date = date - timedelta(days=1)

        return date

    def get_next_business_day(self, date: date):
        while not self.is_business_day(date):
            date = date + timedelta(days=1)

        return date
