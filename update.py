from datetime import datetime
import time

import calendar
import pandas as pd

from api.ids import porsche_id
from tools import os, load_dcm, merge_with_prisma, merge_with_programmatic, write_to_spreadsheet
from tools.constants import final_report_path


class Timer(object):

    def __enter__(self, *ars):
        self.start = time.time()

    def __exit__(self, *ars):
        self.end = time.time()
        print(round(self.end - self.start, 4), "s", sep='')


if __name__ == '__main__':

    with Timer():
        module_path = os.path.split(__file__)[0]

        dcm_cum = load_dcm(148235570, porsche_id, force_run=True)
        dcm_prev_month = load_dcm(149683748, porsche_id, force_run=True)

        prev_month = dcm_cum.date_range[1]
        suffixes = ['', f'_{prev_month.strftime("%B")}']

        df = dcm_cum.merge(dcm_prev_month, left_on='Placement', right_on='Placement', suffixes=suffixes)

        data = merge_with_prisma(df)
        data = merge_with_programmatic(data, "tools/inputs/programmatic_reports/PHD - Porsche - FY18 Macan- Delivery Report Jul  16 - 31.xlsx")

        for col in data.columns:
            if 'Date' in col:
                data[col] = pd.to_datetime(data[col])

        def dt_to_timestamp(year, month, day):
            return pd.to_datetime(datetime(year, month, day))

        def pacing_algorithm(row):

            end_of_month = dcm_cum.date_range[1]

            if row['Placement Start Date'].month == row['Placement End Date'].month:
                numerator = 1
                denominator = 1

            elif row['Placement End Date'] < end_of_month:
                numerator = row['Placement End Date'] - dt_to_timestamp(row['Placement End Date'].year, row['Placement End Date'].month, 1)
                numerator = numerator.days

                denominator = calendar.monthrange(row['Placement End Date'].year, row['Placement End Date'].month)[1]

            else:
                numerator = min(end_of_month.day - row['Placement Start Date'].day,
                                calendar.monthrange(datetime.today().year, end_of_month.month)[1])
                # numerator = calendar.monthrange(datetime.today().year, end_of_month.month)[1]
                denominator = row['Placement End Date'] - row['Placement Start Date']
                denominator = denominator.days

            return round(numerator / denominator * row['Planned Units'], 0)

        data['Monthly Commitment'] = data.apply(pacing_algorithm, axis=1)
        data['Media Type'] = data['Placement'].str.split('_').apply(lambda x: x[0])

        write_to_spreadsheet(df=data,
                             book_path=os.path.join(final_report_path, "Monthly_Porsche_Report_Final.xlsm"),
                             sheet="Raw Data",
                             range="A$1")
