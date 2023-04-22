from setuptools import setup, find_packages

setup(
    name='transaction-accounts',
    version='0.0.3',
    description='Create configuration for transactional accounts and implement account runtime',
    long_description='''
Transaction Accounts
====================

This library provides basic functionality for working with transaction
accounts.

You can use it to make any type of transaction account, such as a
savings account, a credit card, or a loan.

Assume we would like to create simple Savings Account that has 3 types
of balances: 
- current balance 
- interest accrued 
- withholding tax

We would like to have 4 types of transactions: 
- deposit 
- interest accrued 
- interest capitalized 
- withholding tax

We would like to have 2 types of schedules: 
- accrual schedule 
- compounding schedule

We would like to have interest rate with 3 tiers: 
- 0 - 10000: 3% 
- 10000 - 50000: 3.5% 
- 50000+: 4%

Deposit transaction will increase current balance, and it will be used
to deposit money to the account. This transaction will be externally
created and posted to the account.

Interest accrued transaction will increase interest accrued balance, and
it will be used to accrue interest on the account.

Interest will be accrued daily, and it will be calculated based on
current balance and interest rate.

Interest capitalized transaction will increase current balance and
decrease interest accrued balance. This transaction will be internally
created and posted to the account at the end of each month.

Withholding tax transaction will decrease withholding tax balance, and
it will be used to pay withholding tax on the account. It will be
calculated as 20% of interest capitalized transaction.

We will use accrual schedule to accrue interest daily, and we will use
compounding schedule to capitalize interest at the end of each month.

We will use interest rate to calculate interest.

We will use trigger transaction to calculate withholding tax.

Note that this framework is not limited to this configuration, and it
can be used to create any type of transaction account.

You can define custom calculations when calculating either schedules or
transactions. In this context you can use any of the following
variables: - account: Account - transaction: Transaction - config:
Configuration

Here is a code that will create this configuration:

.. code:: python

   def create_savings_account() -> Configuration:
       config: Configuration = Configuration("v1")

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

       accrual_schedule = ScheduleType("accrual", "Accrual Schedule", ScheduleFrequency.DAILY, ScheduleEndType.NO_END,
                                       BusinessDayAdjustment.NO_ADJUSTMENT, "1", "account.start_date")

       savings_account.add_schedule_type(accrual_schedule)

       compounding_schedule = ScheduleType("compounding", "Compounding Schedule", ScheduleFrequency.MONTHLY,
                                           ScheduleEndType.NO_END, BusinessDayAdjustment.NO_ADJUSTMENT, "1",
                                           "account.start_date + relativedelta(month=+1) + relativedelta(days=-1)")

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

Given configuration, we can create an account:

.. code:: python


       config: Configuration = create_savings_account()

       account_type = config.get_account_type("savingsAccount")
       
       # account will start on 1st of January 2019
       account = Account(date(2019, 1, 1), account_type, config)
       
       # we will create account valuation on 1st of January 2020 (action date)
       valuation = AccountValuation(account, account_type, config, date(2020, 1, 1))
       
       deposit_transaction_type = config.get_transaction_type("deposit")
       
       # we will deposit 1000 on 1st of January 2019 (backdated transaction so that we can test accruals)
       external_transactions = group_by_date([
           ExternalTransaction(deposit_transaction_type.name, Decimal(1000), date(2019, 1, 1))])
       
       # we will forecast balances and transactions as of 1st of January 2020
       valuation.forecast(date(2020, 1, 1), external_transactions)
       
       self.assertAlmostEqual(account.positions['current'].amount, Decimal(1030.41), places=1)
       self.assertAlmostEqual(account.positions['withholding'].amount, Decimal(30.41) * Decimal(0.2), places=1)
    
    ''',
    author='Igor Music',
    author_email='igormusich@gmail.com',
    packages=find_packages(),
    license='MIT',
    url='https://github.com/igormusic/transaction-accounts',
    download_url='https://github.com/igormusic/transaction-accounts/archive/refs/tags/0.0.3.tar.gz',
    keywords=['TRANSACTION PROCESSING', 'LOANS', 'SAVINGS', 'ACCOUNTS', 'FINANCE', 'BANKING'],
    install_requires=[
        'python-dateutil',
        'dataclasses-json'
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',  # Define that your audience are developers
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.9',

    ],
)
