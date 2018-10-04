# programmatic.py
import os
import pandas as pd
import numpy as np
import warnings

from .config import prog_report_path

report_files = list(os.walk(prog_report_path))[-1][-1]
programmatic_report_files = [os.path.join(prog_report_path, file) for file in report_files]


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


def get_programmatic_placement_column(df):
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
        raise ValueError(f"Multiple placement columns found: {cols}. Make sure only one column has the DCM placement name.")


def get_prog_spend_df(path_to_report):
    df = pd.read_excel(path_to_report, sheet_name="Raw Data")

    for col in df.columns:
        if np.issubdtype(df[col].dtype, np.number):
            df[col] = pd.to_numeric(df[col])

    placement_column = get_programmatic_placement_column(df)

    if not placement_column:
        return None
    else:
        df_spend = pd.DataFrame(df.groupby([placement_column])["Spend"].sum())
        return df_spend
