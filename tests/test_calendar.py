import unittest
from datetime import date

from accounts.runtime import BusinessDayCalculation
from tests.test_config import get_euro_calendar


class TestCalendar(unittest.TestCase):

    def test_long_weekend(self):
        calendar = get_euro_calendar()

        self.assertTrue(calendar.is_business_day(date(2019, 4, 18)))
        self.assertFalse(calendar.is_business_day(date(2019, 4, 19)))  # easter friday
        self.assertFalse(calendar.is_business_day(date(2019, 4, 20)))  # saturday
        self.assertFalse(calendar.is_business_day(date(2019, 4, 21)))  # sunday
        self.assertFalse(calendar.is_business_day(date(2019, 4, 22)))  # eastern monday
        self.assertTrue(calendar.is_business_day(date(2019, 4, 23)))

        self.assertEqual(date(2019, 4, 23), calendar.get_next_business_day(date(2019, 4, 19)))
        self.assertEqual(date(2019, 4, 18), calendar.get_previous_business_day(date(2019, 4, 22)))

        self.assertEqual(date(2019, 4, 23),
                         calendar.get_calculated_business_day(date(2019, 4, 19),
                                                              BusinessDayCalculation.NEXT_BUSINESS_DAY))
        self.assertEqual(date(2019, 4, 18),
                         calendar.get_calculated_business_day(date(2019, 4, 22),
                                                              BusinessDayCalculation.PREVIOUS_BUSINESS_DAY))

        self.assertEqual(date(2019, 4, 18),
                         calendar.get_calculated_business_day(date(2019, 4, 20),
                                                              BusinessDayCalculation.CLOSEST_BUSINESS_DAY_OR_NEXT))
        self.assertEqual(date(2019, 4, 23),
                         calendar.get_calculated_business_day(date(2019, 4, 21),
                                                              BusinessDayCalculation.CLOSEST_BUSINESS_DAY_OR_NEXT))

        self.assertEqual(date(2019, 8, 30),
                         calendar.get_calculated_business_day(date(2019, 8, 31),
                                                              BusinessDayCalculation.
                                                              NEXT_BUSINESS_DAY_THIS_MONTH_OR_PREVIOUS))

        self.assertEqual(date(2019, 9, 30),
                         calendar.get_calculated_business_day(date(2019, 9, 29),
                                                              BusinessDayCalculation.
                                                              NEXT_BUSINESS_DAY_THIS_MONTH_OR_PREVIOUS))

        self.assertEqual(date(2019, 9, 29),
                         calendar.get_calculated_business_day(date(2019, 9, 29),
                                                              BusinessDayCalculation.
                                                              ANY_DAY))  # no adjustment, non-working day is ok
