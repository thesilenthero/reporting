import csv

import os
import pandas as pd
import numpy as np
from datetime import datetime
import parsedatetime as pdt
import xlwings as xw

from .prisma import MediaPlan, get_media_plan_files
from .constants import dcm_report_path, prog_report_path, plan_path
from api import run_and_download_report, Report

import warnings

report_files = list(os.walk(prog_report_path))[-1][-1]
programmatic_report_files = [os.path.join(prog_report_path, file) for file in report_files]


def parse_datestr(datestr):
    cal = pdt.Calendar()
    return datetime(*cal.parse(datestr)[0][:6])


def spread_units(df, left_columns, right_column):
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

    >>> spread_units(df, ['Col1'], 'Col2')
    >>>
    0     333.333333
    1     333.333333
    2     333.333333
    3    1000.000000
    4    1000.000000
    dtype: float64
    """

    if isinstance(left_columns, str):
        left_columns = [left_columns]

    mapping = df.groupby(left_columns).count()
    counts = df.apply(lambda row: mapping.loc[tuple(row[left_columns])][right_column], axis=1)

    return df[right_column] / counts


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


def load_dcm(report_id, profile_id, path=None, force_run=False):

    filename = Report(profile_id, report_id).name + ".csv"

    if path is None:
        path = os.path.join(dcm_report_path, filename)

    if not os.path.isfile(path) or force_run is True:
        run_and_download_report(report_id, profile_id, path)

    df = load_from_csv(path)

    return df


def merge_with_prisma(df, plan='default', join_on=None):

    if join_on is None:
        join_on = ["Campaign", "Placement"]
    elif "Placement" not in join_on:
        raise ValueError("Reports must be merged by at least the placement level")

    if plan == 'default':
        plans = [MediaPlan(file) for file in get_media_plan_files(plan_path)]
    else:
        if isinstance(plan, str):
            plans = [MediaPlan(plan)]
        else:
            plans = [MediaPlan(file) for file in plan]

    parsed_plans = []

    for plan in plans:
        plan.parse()
        parsed_plans.extend(plan.output)

    df2 = pd.DataFrame(parsed_plans, columns=["Campaign", "Placement", "Planned Units", "Planned Cost", "Rate", "Placement Start Date", "Placement End Date"])

    df.sort_values(['Site (DCM)', 'Placement'], inplace=True)
    df = df.merge(df2.drop_duplicates(), how="left", left_on=join_on,
                  right_on=join_on)
    return df
    # df.fillna(0, inplace=True)


def merge_with_programmatic(dcm_data, prog_report="default", join_on=None):

    if join_on is None:
        join_on = ["Placement"]
    elif "Placement" not in join_on:
        raise ValueError("Reports must be merged by at least the placement level")

    if prog_report == 'default':
        prog_spends = [get_prog_spend_df(file) for file in programmatic_report_files]

    else:
        if isinstance(prog_report, str):
            prog_spends = [get_prog_spend_df(prog_report)]
        else:
            prog_spends = [get_prog_spend_df(file) for file in prog_report]

    prog_spend = pd.concat(prog_spends, axis=0)
    spend_mapping = prog_spend.to_dict('index')

    def mappingfunc(row):
        if spend_mapping.get(row['Placement']):
            return spend_mapping.get(row['Placement']).get('Spend')
        else:
            return row['Media Cost']

    dcm_data['Media Cost'] = dcm_data.apply(mappingfunc, axis=1)

    return dcm_data


def get_placement_column(df):
    cols = []

    for col in df.columns:
        try:
            warnings.filterwarnings('ignore')

            if set(df[col].str.contains(r"_ACCUEN CANADA(\s\(CDN\$\))?_")) == {True}:
                cols.append(col)
        except AttributeError:
            pass

    if len(cols) == 1:
        return cols[0]
    else:
        raise ValueError(f"Multiple placement columns detected: {cols}. Make sure only one column has the DCM placement name.")


def get_prog_spend_df(path_to_report):
    df = pd.read_excel(path_to_report, sheet_name="Raw Data")

    for col in df.columns:
        if np.issubdtype(df[col].dtype, np.number):
            df[col] = pd.to_numeric(df[col])

    placement_column = get_placement_column(df)

    if not placement_column:
        return None
    else:
        df_spend = pd.DataFrame(df.groupby([placement_column])["Spend"].sum())
        return df_spend


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
