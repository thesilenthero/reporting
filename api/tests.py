from datetime import datetime, timedelta
import json
import unittest

import api

test_report = api.Report(4613164, 162405225)


class ReportSetDateRangeTests(unittest.TestCase):

    def test_set_date_range_fixed(self):

        end = datetime.today() - timedelta(days=1)
        start = end - timedelta(days=7)

        test_report.set_date_range(start.strftime("%Y-%m-%d"),
                                   end.strftime("%Y-%m-%d"))

        new_start = test_report.body["criteria"]["dateRange"]["startDate"]
        new_end = test_report.body["criteria"]["dateRange"]["endDate"]

        self.assertEqual(new_start, start.strftime("%Y-%m-%d"))
        self.assertEqual(new_end, end.strftime("%Y-%m-%d"))

    def test_set_date_range_relative(self):
        relative_range = "last_30_days"

        test_report.set_date_range(period=relative_range)
        new_relative_range = test_report.body['criteria']['dateRange'].get('relativeDateRange')

        self.assertIsNotNone(new_relative_range)
        self.assertEqual(new_relative_range, "LAST_30_DAYS")

    def test_start_and_end_and_period_error(self):
        with self.assertRaises(ValueError):
            test_report.set_date_range(start="start", end="end", period="period")

    def test_start_and_period_error(self):
        with self.assertRaises(ValueError):
            test_report.set_date_range(start="start", period="period")

    def test_end_and_period_error(self):
        with self.assertRaises(ValueError):
            test_report.set_date_range(end="end", period="period")

    def test_no_parameters_supplied_error(self):
        with self.assertRaises(ValueError):
            test_report.set_date_range()


class ReportTests(unittest.TestCase):

    def test_set_dimensions(self):
        dimensions = ["Advertiser", "Campaign", "Site (DCM)"]
        test_report.set_dimensions(dimensions)

        with open("standard_dimensions.json", "r") as f:
            standard_dimensions = json.load(f)

        api_dim_names = [standard_dimensions[dim.lower()]['API Name'] for dim in dimensions]
        new_dimensions = test_report.body['criteria']['dimensions']

        for api_dim_name in api_dim_names:
            self.assertIn(api_dim_name, [x['name'] for x in new_dimensions])


if __name__ == '__main__':
    unittest.main()
