from calendar import monthrange
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import List, Optional, Dict
from pydantic import BaseModel

from accounts.utility import CustomEncoder


class TransactionOperation(Enum):
    CREDIT = 'credit'
    DEBIT = 'debit'
    SET = 'set'


class DataType(Enum):
    DECIMAL = 'decimal'
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


class PositionType(BaseModel):
    name: str
    label: str


class DateType(BaseModel):
    name: str
    label: str
    required: bool = True


class RateTier(BaseModel):
    from_amount: Decimal
    to_amount: Decimal
    rate: Decimal


class RateType(BaseModel):
    name: str
    label: str
    rate_tiers: Dict[str, List[RateTier]] = {}

    class Config:
        json_encoders = {Dict: CustomEncoder()}

    @staticmethod
    def __get_key(value_date):
        return value_date.strftime("%Y-%m-%d")

    def add_tier(self, value_date: date, to_amount: Decimal, rate: Decimal):
        key = self.__get_key(value_date)
        if key not in self.rate_tiers:
            self.rate_tiers[key] = []

        rate_tier = RateTier(from_amount=self.get_max_to_amount(value_date), to_amount=to_amount, rate=rate)
        self.rate_tiers[key].append(rate_tier)

    def get_max_to_amount(self, value_date: date):
        key = self.__get_key(value_date)
        if key not in self.rate_tiers:
            return Decimal(0)

        rate_tiers = self.rate_tiers[key]

        if len(rate_tiers) == 0:
            return Decimal(0)

        max_value = max(rate_tiers, key=lambda tier: tier.to_amount)
        return max_value.to_amount

    def __get_tiers(self, value_date) -> List[RateTier]:
        # find first date that is less than or equal to value_date
        key = self.__get_key(value_date)
        dates = [d for d in self.rate_tiers.keys() if d <= key]
        if len(dates) == 0:
            raise Exception(f"No rate tiers found for date {str(value_date)} in rate table {self.name}")
        index_date = max(dates)
        return self.rate_tiers[index_date]

    def get_rate(self, value_date: date, amount: Decimal) -> Decimal:
        applicable_tiers = (rt for rt in self.__get_tiers(value_date) if rt.from_amount <= amount <= rt.to_amount)

        # if no tiers are applicable, raise an exception
        rate_tier = next(applicable_tiers, None)
        if rate_tier is None:
            if amount < Decimal(0):
                return Decimal(0)
            else:
                raise Exception(
                    f"No rate tiers found for amount {str(amount)} on date {str(value_date)} in rate table {self.name}")

        return rate_tier.rate

    def get_daily_fee(self, users: Decimal, value_date: date):
        _, days_in_month = monthrange(value_date.year, value_date.month)
        monthly_fee = Decimal(self.get_fee(value_date, Decimal(0), users))
        return monthly_fee / Decimal(days_in_month)

    def get_fee(self, value_date: date, from_amount: Decimal, to_amount: Decimal):
        processed = from_amount
        fee = Decimal(0)

        exit_loop = False

        for rate_tier in self.__get_tiers(value_date):
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


class PositionRule(BaseModel):
    operation: TransactionOperation
    position_type_name: str


class TransactionType(BaseModel):
    name: str
    label: str
    position_rules: List[PositionRule] = []
    maximum_precision: bool = False

    def add_position_rule(self, transaction_operation: TransactionOperation, position_type: PositionType):
        self.position_rules.append(PositionRule(operation=transaction_operation, position_type_name=position_type.name))
        return self


class ScheduleType(BaseModel):
    name: str
    label: str
    frequency: ScheduleFrequency
    end_type: ScheduleEndType
    business_day_adjustment: BusinessDayAdjustment
    interval_expression: str
    start_date_expression: str
    end_date_expression: str = None
    number_of_repeats_expression: str = None
    include_dates_expression: str = None
    exclude_dates_expression: str = None
    editable: bool = True


class ScheduledTransaction(BaseModel):
    schedule_name: str
    timing: ScheduledTransactionTiming
    generated_transaction_type: str
    amount_expression: str


class TriggeredTransaction(BaseModel):
    trigger_transaction_type_name: str
    generated_transaction_type: str
    amount_expression: str


class PropertyType(BaseModel):
    name: str
    label: str
    data_type: DataType
    required: bool = True
    value_dated: bool = False


class InstalmentType(BaseModel):
    name: str
    label: str
    timing: ScheduledTransactionTiming
    schedule_name: str
    transaction_type: str
    property_name: str
    solve_for_zero_position: str
    solve_for_date: str


class AccountType(BaseModel):
    name: str
    label: str
    transaction_types: List[TransactionType] = []
    position_types: List[PositionType] = []
    date_types: List[DateType] = []
    rate_types: Dict[str, RateType] = {}
    triggered_transactions: List[TriggeredTransaction] = []
    schedule_types: List[ScheduleType] = []
    property_types: List[PropertyType] = []
    scheduled_transactions: List[ScheduledTransaction] = []
    instalment_type: InstalmentType = None

    def add_property_type(self, name: str, label: str, data_type: DataType, required: bool = True) -> PropertyType:
        property_type = PropertyType(name=name, label=label, data_type=data_type.value, required=required)
        self.property_types.append(property_type)
        return property_type

    def add_date_type(self, name: str, label: str) -> DateType:
        date_type = DateType(name=name, label=label)
        self.date_types.append(date_type)
        return date_type

    def add_transaction_type(self, name: str, label: str, maximum_precision: bool = False) -> TransactionType:
        transaction_type = TransactionType(name=name, label=label, maximum_precision=maximum_precision)
        self.transaction_types.append(transaction_type)
        return transaction_type

    def add_position_type(self, name: str, label: str) -> PositionType:
        position_type = PositionType(name=name, label=label)
        self.position_types.append(position_type)
        return position_type

    def add_rate_type(self, name: str, label: str) -> RateType:
        rate_type = RateType(name=name, label=label)
        self.rate_types[name] = rate_type
        return rate_type

    def add_trigger_transaction(self, trigger_transaction_type: TransactionType,
                                generated_transaction_type: TransactionType, amount_expression: str):
        trigger_transaction = TriggeredTransaction(trigger_transaction_type_name=trigger_transaction_type.name,
                                                   generated_transaction_type=generated_transaction_type.name,
                                                   amount_expression=amount_expression)
        self.triggered_transactions.append(trigger_transaction)

    def add_schedule_type(self, schedule_type: ScheduleType):
        self.schedule_types.append(schedule_type)

    def add_scheduled_transaction(self, schedule_type: ScheduleType, timing: ScheduledTransactionTiming,
                                  generated_transaction_type: TransactionType, amount_expression: str):
        scheduled_transaction = ScheduledTransaction(schedule_name=schedule_type.name, timing=timing,
                                                     generated_transaction_type=generated_transaction_type.name,
                                                     amount_expression=amount_expression)
        self.scheduled_transactions.append(scheduled_transaction)

    def get_transaction_type(self, transaction_type_name: str) -> TransactionType:
        return next(tt for tt in self.transaction_types if tt.name == transaction_type_name)

    def get_rate_type(self, rate_type_name: str):
        return next(rt for rt in self.rate_types if rt.name == rate_type_name)

    def get_trigger_transaction(self, trigger_transaction_type_name: str) -> Optional[TriggeredTransaction]:
        return next((tt for tt in self.triggered_transactions if
                     tt.trigger_transaction_type_name == trigger_transaction_type_name), None)

    def add_instalment_type(self, name: str, label: str, timing: ScheduledTransactionTiming,
                            transaction_type: str, property_name: str,
                            solve_for_zero_position: str, solve_for_date: str,
                            schedule_name: str) -> InstalmentType:

        instalment_type = InstalmentType(name=name, label=label, timing=timing,
                                         transaction_type=transaction_type,
                                         property_name=property_name,
                                         schedule_name=schedule_name,
                                         solve_for_zero_position=solve_for_zero_position,
                                         solve_for_date=solve_for_date)
        self.instalment_type = instalment_type

    def __getattr__(self, method_name):
        if method_name in self.rate_types:
            return self.rate_types[method_name]
        else:
            raise AttributeError(f'No such attribute: {method_name}')
