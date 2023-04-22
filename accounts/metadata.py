from calendar import monthrange
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from dataclasses_json import dataclass_json


class TransactionOperation(Enum):
    CREDIT = 'credit'
    DEBIT = 'debit'
    SET = 'set'


class DataType(Enum):
    NUMBER = 'number'
    STRING = 'string'
    BOOLEAN = 'boolean'


class ScheduleEndType(Enum):
    NO_END = "no_end"
    END_REPEATS = "end_repeats"
    END_DATE = "end_date"


class BusinessDayAdjustment(Enum):
    NO_ADJUSTMENT = "no_adjustment"
    NEXT_WORKING_DAY = "next_working_day"
    PREVIOUS_WORKING_DAY = "previous_working_day"
    CLOSEST_WORKING_DAY = "closest_working_day"


class ScheduleFrequency(Enum):
    DAILY = "daily"
    MONTHLY = "monthly"


class ScheduledTransactionTiming(Enum):
    START_OF_DAY = "start_of_day"
    END_OF_DAY = "end_of_day"


@dataclass_json()
@dataclass()
class PositionType:
    name: str
    label: str


@dataclass_json()
@dataclass()
class RateTier:
    from_amount: Decimal
    to_amount: Decimal
    rate: Decimal


@dataclass_json()
@dataclass()
class RateType:
    name: str
    label: str
    rate_tiers: List[RateTier] = field(default_factory=list)

    def add_tier(self, to_amount: Decimal, rate: Decimal):
        rate_tier = RateTier(self.get_max_to_amount(), to_amount, rate)
        self.rate_tiers.append(rate_tier)

    def get_max_to_amount(self):
        if len(self.rate_tiers) == 0:
            return Decimal(0)

        max_value = max(self.rate_tiers, key=lambda tier: tier.to_amount)
        return max_value.to_amount

    def get_rate(self, amount: Decimal):
        rate_tier = next(rt for rt in self.rate_tiers if rt.from_amount <= amount <= rt.to_amount)

        return rate_tier.rate

    def get_daily_fee(self, users: Decimal, value_date: date):
        _, days_in_month = monthrange(value_date.year, value_date.month)
        monthly_fee = Decimal(self.get_fee(Decimal(0), users))
        return monthly_fee / Decimal(days_in_month)

    def get_fee(self, from_amount: Decimal, to_amount: Decimal):
        processed = from_amount
        fee = Decimal(0)

        exit_loop = False

        for rate_tier in self.rate_tiers:
            if rate_tier.from_amount <= processed < rate_tier.to_amount:
                part_processed = rate_tier.to_amount - processed

                if to_amount < rate_tier.to_amount:
                    part_processed = to_amount - processed
                    exit_loop = True

                fee = fee + part_processed * rate_tier.rate
                processed = processed + part_processed

                if exit_loop:
                    break

        return fee


@dataclass_json()
@dataclass()
class PositionRule:
    operation: TransactionOperation
    position_type_name: str


@dataclass_json()
@dataclass()
class TransactionType:
    name: str
    label: str
    position_rules: List[PositionRule] = field(default_factory=list)

    def add_position_rule(self, transaction_operation: TransactionOperation, position_type: PositionType):
        self.position_rules.append(PositionRule(transaction_operation, position_type.name))
        return self


@dataclass_json()
@dataclass()
class ScheduleType:
    name: str
    label: str
    frequency: ScheduleFrequency
    end_type: ScheduleEndType
    business_day_adjustment: BusinessDayAdjustment
    interval_expression: str
    start_date_expression: str
    end_date_expression: str = field(default=None)
    number_of_repeats_expression: str = field(default=None)
    include_dates_expression: str = field(default=None)
    exclude_dates_expression: str = field(default=None)


@dataclass_json()
@dataclass()
class ScheduledTransaction:
    schedule_name: str
    timing: ScheduledTransactionTiming
    generated_transaction_type: str
    amount_expression: str


@dataclass_json()
@dataclass()
class TriggeredTransaction:
    trigger_transaction_type_name: str
    generated_transaction_type: str
    amount_expression: str


@dataclass_json()
@dataclass()
class PropertyType:
    name: str
    label: str


@dataclass_json()
@dataclass()
class AccountType:
    name: str
    label: str
    transaction_type_names: List[str] = field(default_factory=list)
    schedule_types: List[ScheduleType] = field(default_factory=list)
    property_types: List[PropertyType] = field(default_factory=list)
    scheduled_transactions: List[ScheduledTransaction] = field(default_factory=list)
    triggered_transactions: List[TriggeredTransaction] = field(default_factory=list)

    def add_transaction_type(self, transaction_type: TransactionType):
        self.transaction_type_names.append(transaction_type.name)

    def add_schedule_type(self, schedule_type: ScheduleType):
        self.schedule_types.append(schedule_type)

    def add_scheduled_transaction(self, schedule_type: ScheduleType, timing: ScheduledTransactionTiming,
                                  generated_transaction_type: TransactionType, amount_expression: str):
        scheduled_transaction = ScheduledTransaction(schedule_type.name, timing, generated_transaction_type.name,
                                                     amount_expression)
        self.scheduled_transactions.append(scheduled_transaction)

    def add_trigger_transaction(self, trigger_transaction_type: TransactionType,
                                generated_transaction_type: TransactionType, amount_expression: str):
        triggered_transaction = TriggeredTransaction(trigger_transaction_type.name, generated_transaction_type.name,
                                                     amount_expression)
        self.triggered_transactions.append(triggered_transaction)


@dataclass_json()
@dataclass()
class Configuration:
    version: str
    transaction_types: List[TransactionType] = field(default_factory=list)
    position_types: List[PositionType] = field(default_factory=list)
    account_types: List[AccountType] = field(default_factory=list)
    rate_types: dict[str,RateType] = field(default_factory=dict)
    triggered_transactions: List[TriggeredTransaction] = field(default_factory=list)

    def add_transaction_type(self, name: str, label: str) -> TransactionType:
        transaction_type = TransactionType(name, label)
        self.transaction_types.append(transaction_type)
        return transaction_type

    def add_position_type(self, name: str, label: str) -> PositionType:
        position_type = PositionType(name, label)
        self.position_types.append(position_type)
        return position_type

    def add_account_type(self, name: str, label: str) -> AccountType:
        account_type = AccountType(name, label)
        self.account_types.append(account_type)
        return account_type

    def add_rate_type(self, name: str, label: str) -> RateType:
        rate_type = RateType(name, label)
        self.rate_types[name] = rate_type
        return rate_type

    def add_trigger_transaction(self, trigger_transaction_type: TransactionType,
                                generated_transaction_type: TransactionType, amount_expression: str):
        trigger_transaction = TriggeredTransaction(trigger_transaction_type.name, generated_transaction_type.name,
                                                   amount_expression)
        self.triggered_transactions.append(trigger_transaction)

    def get_transaction_type(self, transaction_type_name: str) -> TransactionType:
        return next(tt for tt in self.transaction_types if tt.name == transaction_type_name)

    def get_account_type(self, account_type_name: str):
        return next(at for at in self.account_types if at.name == account_type_name)

    def get_rate_type(self, rate_type_name: str):
        return next(rt for rt in self.rate_types if rt.name == rate_type_name)

    def get_trigger_transaction(self, trigger_transaction_type_name: str)-> Optional[TriggeredTransaction]:
        return next((tt for tt in self.triggered_transactions if tt.trigger_transaction_type_name == trigger_transaction_type_name), None)

    def __getattr__(self, method_name: str):
        # find rate type by method name

        if method_name in self.rate_types:
            return self.rate_types[method_name]
        else:
            raise AttributeError(f'No such attribute: {method_name}')