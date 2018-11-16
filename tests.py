from datetime import datetime, timedelta
import json
import unittest

import pandas as pd

import api
import tools


class TestReportTestCase(unittest.TestCase):

    test_report = api.Report(4613164, 162405225)


class ReportTests(TestReportTestCase):

    def test_set_dimensions(self):

        self.test_report.set_dimensions(["Placement", "Creative"])

        dimensions = ["Advertiser", "Campaign", "Site (DCM)"]
        self.test_report.set_dimensions(dimensions)

        with open("api/standard_dimensions.json", "r") as f:
            standard_dimensions = json.load(f)

        api_dim_names = [standard_dimensions[dim.lower()]['API Name'] for dim in dimensions]
        new_dimensions = self.test_report.body['criteria']['dimensions']

        for api_dim_name in api_dim_names:
            self.assertIn(api_dim_name, [x['name'] for x in new_dimensions])


class ReportSetDateRangeTests(TestReportTestCase):

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

        self.test_report.set_date_range(period="last_90_days")

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


class ToolsTests(unittest.TestCase):

    test_df = pd.DataFrame({'col1': ['a', 'a', 'a', 'b', 'b', 'c', 'c', 'c', 'c', ],
                            'col2': ['x', 'y', 'z', 'x', 'y', 'x', 'y', 'z', 'u'],
                            'col3': [1, 2, 3, 1, 2, 1, 2, 3, 4],
                            'col4': [10, 10, 10, 10, 10, 10, 10, 10, 10, ]})

    def test_redistribute_units_function_one_left_dimension(self):

        results = round(tools.redistribute_units(self.test_df, 'col1', 'col4'), 3)

        correct_answers = [3.333, 3.333, 3.333, 5.0, 5.0, 2.5, 2.5, 2.5, 2.5]
        for result, answer in zip(results, correct_answers):
            self.assertEqual(result, answer)

    def test_redistribute_units_function_one_left_dimension_as_list(self):

        results = round(tools.redistribute_units(self.test_df, ['col1'], 'col4'), 3)

        correct_answers = [3.333, 3.333, 3.333, 5.0, 5.0, 2.5, 2.5, 2.5, 2.5]
        for result, answer in zip(results, correct_answers):
            self.assertEqual(result, answer)


    def test_redistribute_units_function_multi_left_dimension(self):
        results = tools.redistribute_units(self.test_df, ['col1', 'col2'], 'col4')
        correct_answers = [10, 10, 10, 10, 10, 10, 10, 10, 10, ]
        for result, answer in zip(results, correct_answers):
            self.assertEqual(result, answer)

    def test_redistribute_units_function_weighted_parameter(self):

        results = round(tools.redistribute_units(self.test_df, 'col1', 'col4', weight_against='col3'), 3)

        correct_answers = [1.667, 3.333, 5.0, 3.333, 6.667, 1.0, 2.0, 3.0, 4.0]
        for result, answer in zip(results, correct_answers):
            self.assertEqual(result, answer)

    def test_redistribute_units_function_weight_parameter_multidimension(self):
        results = tools.redistribute_units(self.test_df, ['col1', 'col2'], 'col4',
                                           weight_against='col3')
        correct_answers = [10, 10, 10, 10, 10, 10, 10, 10, 10, ]
        for result, answer in zip(results, correct_answers):
            self.assertEqual(result, answer)

    def test_merge_with_programmatic_function_merge_on_error(self):

        with self.assertRaises(ValueError):
            tools.merge_with_programmatic_report("prog_report_path", "Raw Data", "df",
                                                 merge_on=["Date"])


class MiscellaneousTests(unittest.TestCase):

    period_map = pd.DataFrame([
        {'end': pd.Timestamp('2018-10-07 00:00:00'),
         'period': 'Sept 17 - Oct 7',
         'start': pd.Timestamp('1900-01-01 00:00:00')},
        {'end': pd.Timestamp('2018-11-04 00:00:00'),
         'period': 'Oct 8 - Nov 4',
         'start': pd.Timestamp('2018-10-08 00:00:00')},
        {'end': pd.Timestamp('2018-12-02 00:00:00'),
         'period': 'Nov 5 - Dec 2',
         'start': pd.Timestamp('2018-11-05 00:00:00')},
        {'end': pd.Timestamp('2018-12-30 00:00:00'),
         'period': 'Dec 3 - 30',
         'start': pd.Timestamp('2018-12-03 00:00:00')},
        {'end': pd.Timestamp('2019-01-27 00:00:00'),
         'period': 'Dec 31 - Jan 27',
         'start': pd.Timestamp('2018-12-31 00:00:00')},
        {'end': pd.Timestamp('2019-02-24 00:00:00'),
         'period': 'Jan 28 - Feb 24',
         'start': pd.Timestamp('2019-01-28 00:00:00')},
        {'end': pd.Timestamp('2019-03-31 00:00:00'),
         'period': 'Feb 25 - March 31',
         'start': pd.Timestamp('2019-02-25 00:00:00')}

    ])

    def get_period_from_daterange(self, value):

        result = self.period_map.loc[(self.period_map.loc[:, "start"] <= value) &
                                     (value <= self.period_map.loc[:, "end"]), "period"].iloc[0]
        return result

    def test_get_period_from_daterange(self):

        periods = [(pd.Timestamp("September 19, 2018"), "Sept 17 - Oct 7"),
                   (pd.Timestamp("October 19, 2018"), "Oct 8 - Nov 4"),
                   (pd.Timestamp("November 4, 2018"), "Oct 8 - Nov 4"),
                   (pd.Timestamp("October 7, 2018"), "Sept 17 - Oct 7")]

        for p in periods:

            self.assertEqual(p[1], self.get_period_from_daterange(p[0]))
            self.assertEqual(p[1], self.get_period_from_daterange(p[0]))


if __name__ == '__main__':
    unittest.main()
