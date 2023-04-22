import unittest

from accounts.runtime import *


class TestSchedule(unittest.TestCase):
    start_date = date(2013, 3, 8)
    end_date = start_date + relativedelta(years=+25)

    def __get_daily_schedule(self, start_date: date, end_date: date, end_type: ScheduleEndType):
        return Schedule(start_date= start_date,end_type= end_type,frequency= ScheduleFrequency.DAILY, interval=1,
                        adjustement=BusinessDayAdjustment.NO_ADJUSTMENT, end_date=end_date)

    def test_daily_schedule_no_end_tests(self):
        accrual_schedule = self.__get_daily_schedule(self.start_date, self.end_date, ScheduleEndType.NO_END)

        accrual_dates = accrual_schedule.get_all_dates(self.end_date);

        self.assertEqual(self.start_date, accrual_dates[0])
        self.assertEqual(self.end_date, accrual_dates[len(accrual_dates) - 1])
        self.assertEqual((self.end_date - self.start_date).days + 1, len(accrual_dates))

        self.assertEqual(accrual_schedule.is_due(self.start_date), True)
        self.assertEqual(accrual_schedule.is_due(self.end_date), True)

        self.assertEqual(accrual_schedule.is_due(self.start_date + relativedelta(days=-1)), False)
        self.assertEqual(accrual_schedule.is_due(self.end_date + relativedelta(days=+1)), True)

    def test_monthly_schedule(self):
        interest_start = date(2013, 3, 31)
        schedule = Schedule(start_date=interest_start, end_type=ScheduleEndType.END_DATE, frequency=ScheduleFrequency.MONTHLY,
                            interval=1,end_date=self.end_date)

        schedule.exclude_dates.append(date(2013, 12, 31))
        schedule.include_dates.append(self.end_date)

        interest_dates = schedule.get_all_dates(self.end_date)

        self.assertEqual(schedule.adjustment, BusinessDayAdjustment.NO_ADJUSTMENT)
        self.assertEqual(schedule.frequency, ScheduleFrequency.MONTHLY)
        self.assertEqual(schedule.end_type, ScheduleEndType.END_DATE)
        self.assertEqual(schedule.interval, 1)
        self.assertEqual(schedule.start_date, interest_start)
        self.assertEqual(schedule.end_date, self.end_date)

        self.assertEqual(interest_start, interest_dates[0])
        self.assertEqual(date(2013, 4, 30), interest_dates[1])
        self.assertEqual(date(2013, 5, 31), interest_dates[2])
        self.assertEqual(date(2014, 2, 28), interest_dates[10])
        self.assertEqual(self.end_date, interest_dates[-1])
        self.assertEqual(schedule.is_due(date(2013, 12, 31)), False)

    def test_daily_schedule_with_end_date(self):
        accrual_schedule = self.__get_daily_schedule(self.start_date, self.end_date, ScheduleEndType.END_DATE)

        accrual_dates = accrual_schedule.get_all_dates(self.end_date);

        self.assertEqual(self.start_date, accrual_dates[0])
        self.assertEqual(self.end_date, accrual_dates[len(accrual_dates) - 1])
        self.assertEqual((self.end_date - self.start_date).days + 1, len(accrual_dates))

        self.assertEqual(accrual_schedule.is_due(self.start_date), True)
        self.assertEqual(accrual_schedule.is_due(self.end_date), True)

        self.assertEqual(accrual_schedule.is_due(self.start_date + relativedelta(days=-1)), False)
        self.assertEqual(accrual_schedule.is_due(self.end_date + relativedelta(days=+1)), False)

    def test_monthly_repeats_schedule(self):
        start_date = date(2019, 12, 1)
        discount_schedule = Schedule(start_date=start_date, end_type=ScheduleEndType.END_REPEATS,
                                     frequency= ScheduleFrequency.MONTHLY, interval=1,
                                     adjustment=BusinessDayAdjustment.NO_ADJUSTMENT, number_of_repeats=3)

        discount_dates = discount_schedule.get_all_dates(self.end_date)

        self.assertEqual(len(discount_dates), 3)
        self.assertEqual(date(2020, 2, 1), discount_dates[2])


if __name__ == '__main__':
    unittest.main()
