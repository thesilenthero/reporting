import csv

import os
import pandas as pd
from datetime import datetime
import parsedatetime as pdt
import xlwings as xw

from .prisma import MediaPlan
from .config import dcm_report_path
from api import run_and_download_report, Report

import warnings


def get_files_in_folder(path):
    files = next(os.walk(path))[-1]
    files = [os.path.join(path, file) for file in files]
    return files


def parse_datestr(datestr):
    cal = pdt.Calendar()
    return datetime(*cal.parse(datestr)[0][:6])


def redistribute_units(df, left_columns, right_column, weight_against='na'):
    """
    When combining datasets, some columns might be duplicated. This is a common
    scenario when including planned costs in a DCM report that has more dimensions
    than just placement. DCM doesn't take into account repeated placements and
    the planned values are duplicated and thus inaccurate. This function divides
    a column evenly:
    Example:
    >>> df = DataFrame({'Col1': ['A', 'A', 'A', 'B', 'B'],
                    'Col2': [1000, 1000, 1000, 1000, 1000]})
    >>> df
      Col1  Col2
    0    A  1000
    1    A  1000
    2    A  1000
    3    B  2000
    4    B  2000

    >>> redistribute_units(df, ['Col1'], 'Col2')
    >>>
    0     333.333333
    1     333.333333
    2     333.333333
    3    1000.000000
    4    1000.000000
    dtype: float64
    """

    if weight_against == "na":

        mapping = df.groupby(left_columns).count()
        counts = df.apply(lambda row: mapping.loc[tuple(row[left_columns])][right_column], axis=1)
        return df[right_column] / counts

    else:

        sums = df.groupby(left_columns)[weight_against].sum()
        weights = df.apply(lambda row: row[weight_against] / sums.loc[tuple(row[left_columns])], axis=1)

        return df[right_column] * weights


def load_from_csv(path):

    with open(path, "r") as f:
        reader = csv.reader(f)

        for i, row in enumerate(reader, 1):

            if "Date/Time Generated" in row:
                date_generated = pd.to_datetime(parse_datestr(row[1]))

            if "Date Range" in row:
                date_range = row[1]
                date_range = [x.strip() for x in date_range.split("-")]
                date_range = [pd.to_datetime(parse_datestr(x)) for x in date_range]

            if "Report Fields" in row:
                skiprows = i
                break

    df = pd.read_csv(path, skiprows=skiprows, skipfooter=1, engine='python')

    warnings.filterwarnings('ignore')

    df.date_generated = date_generated
    df.date_range = date_range

    return df


def load_dcm(profileId, reportId, path=None, force_run=False):

    if path is None:
        path = os.path.join(dcm_report_path, Report(profileId, reportId).filename + '.csv')

    if not os.path.isfile(path) or force_run:
        run_and_download_report(profileId, reportId, path=path)

    df = load_from_csv(path)

    return df


def merge_with_prisma(df, plan_path, join_on=None):

    if join_on is None:
        join_on = ["Campaign", "Placement"]

    elif "Placement" not in join_on:
        raise ValueError("Reports must be merged by at least the placement level")

    plan = MediaPlan(plan_path)
    plan.parse()

    plan_df = pd.DataFrame(plan.output, columns=["Campaign", "Placement",
                                                 "Planned Units", "Planned Cost",
                                                 "Rate", "Placement Start Date",
                                                 "Placement End Date"])

    df.sort_values(['Site (DCM)', 'Placement'], inplace=True)
    df = df.merge(plan_df.drop_duplicates(), how="left", left_on=join_on,
                  right_on=join_on)
    return df
    # df.fillna(0, inplace=True)


def write_to_spreadsheet(df, book_path, sheet, cellref="$A$1", clear=True):

    df.index.name = "Index"
    book = xw.Book(book_path)
    sht = book.sheets(sheet)
    if clear:
        sht.clear_contents()

    # rnge = sht.range(cellref)
    # rnge.offset(1, 0).value = df.values
    # rnge.values = list(df.columns)
    sht.range(cellref).value = df
