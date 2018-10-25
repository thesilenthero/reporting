from datetime import datetime, timedelta
import unittest

import api


class ReportSetDateRangeTests(unittest.TestCase):

    test_report = api.Report(4613164, 162405225)

    def test_set_date_range_fixed(self):

        end = datetime.today() - timedelta(days=1)
        start = end - timedelta(days=7)

        self.test_report.set_date_range(start.strftime("%Y-%m-%d"),
                                        end.strftime("%Y-%m-%d"))

        new_start = self.test_report.body["criteria"]["dateRange"]["startDate"]
        new_end = self.test_report.body["criteria"]["dateRange"]["endDate"]

        self.assertEqual(new_start, start.strftime("%Y-%m-%d"))
        self.assertEqual(new_end, end.strftime("%Y-%m-%d"))

    def test_set_date_range_relative(self):
        relative_range = "last_30_days"

        self.test_report.set_date_range(period=relative_range)
        new_relative_range = self.test_report.body['criteria']['dateRange'].get('relativeDateRange')

        self.assertIsNotNone(new_relative_range)
        self.assertEqual(new_relative_range, "LAST_30_DAYS")

    def test_start_and_end_and_period_error(self):
        with self.assertRaises(ValueError):
            self.test_report.set_date_range(start="start", end="end", period="period")

    def test_start_and_period_error(self):
        with self.assertRaises(ValueError):
            self.test_report.set_date_range(start="start", period="period")

    def test_end_and_period_error(self):
        with self.assertRaises(ValueError):
            self.test_report.set_date_range(end="end", period="period")

    def test_no_parameters_supplied_error(self):
        with self.assertRaises(ValueError):
            self.test_report.set_date_range()


if __name__ == '__main__':
    unittest.main()
