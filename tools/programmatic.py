# programmatic.py
import pandas as pd

from .report_readers import redistribute_units


def find_matching_column(df, pattern):
    result = [col for col in df.columns if set(df[col].astype(str).str.match(pattern)) == {True}]

    if not result:
        raise ValueError(f"No column matches '{pattern}'")
    else:
        return result[0]


def merge_with_programmatic_report(prog_filepath, prog_sheet_name, dcm_df, merge_on=['Placement ID'], merge_prog_columns=['Spend']):
    """
    Merge columns from a programmatic report with another report (presumably DCM)

    args:
    - prog_filepath: path to the programmatic report
    - prog_sheet_name: name of the sheet containing the raw data
    - dcm_df: existing dataframe upon which to merge
    - merge_on: common column(s) between the two data sources. Minimum required
    is the placement ID. The function will attempt to find the Placement ID column
    in the programmatic report if it is not named so if it is not named so
    - merge_prog_columns: the columns from the programmatic report being merged.
    By default it is set to ['Spend'], spend being the most common

    """

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
