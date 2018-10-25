# programmatic.py
import os
import pandas as pd

from .config import prog_report_path
from .report_readers import redistribute_units

report_files = list(os.walk(prog_report_path))[-1][-1]
programmatic_report_files = [os.path.join(prog_report_path, file) for file in report_files]


def find_matching_column(df, pattern):
    result = [col for col in df.columns if set(df[col].astype(str).str.match(pattern)) == {True}]

    if not result:
        raise ValueError(f"No column matches '{pattern}'")
    else:
        return result[0]


def merge_with_programmatic_report(prog_filepath, prog_sheet_name, dcm_df, merge_on=['Placement ID'], merge_prog_columns=['Spend']):

    if 'Placement ID' not in merge_on:
        error_message = "The reports have to be merged on at least the Placement ID level."
        raise ValueError(error_message)

    prog_df = pd.read_excel(prog_filepath, sheet_name=prog_sheet_name)

    if 'Date' in prog_df:
        prog_df['Date'] = pd.to_datetime(prog_df['Date'])

    if 'Date' in dcm_df:
        dcm_df['Date'] = pd.to_datetime(dcm_df['Date'])

    placement_id_col = find_matching_column(prog_df, r"^\d{9}$")

    dcm_df['Placement ID'] = dcm_df['Placement ID'].astype(int)
    prog_df[placement_id_col] = prog_df[placement_id_col].astype(int)

    prog_merge_on = merge_on.copy()
    prog_merge_on[prog_merge_on.index('Placement ID')] = placement_id_col

    prog_spend = pd.DataFrame(prog_df.groupby(prog_merge_on)[merge_prog_columns].sum())

    dcm_df = dcm_df.merge(prog_spend, left_on=merge_on, right_index=True, how='left')

    dcm_df['Spend'] = redistribute_units(dcm_df, merge_on, 'Spend')

    return dcm_df
