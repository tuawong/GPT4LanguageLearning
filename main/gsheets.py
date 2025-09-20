from typing import List, Dict, Any, Tuple

import main.Constants as Constants
from  openai import OpenAI
import os
import numpy as np
import pandas as pd
import time

import gspread
import gspread_dataframe as gd
import gspread_formatting as gf
from gspread_formatting import cellFormat, color, textFormat

import os
from io import StringIO
from datetime import datetime


def load_gsheet_dict(
        dict_path: str = None, 
        gsheet_mode=False, 
        gsheet_name = None, 
        worksheet_name = None
        ):
    if gsheet_mode:
        sa = gspread.service_account()
        sh = sa.open(gsheet_name)
        wks = sh.worksheet(worksheet_name)
        current_data = pd.DataFrame(wks.get_all_values())
        current_data.columns = current_data.iloc[0]
        current_data = current_data.iloc[1:]
        return current_data
    
    else:
        if os.path.exists(dict_path):
            return pd.read_csv(dict_path)
        else:
            return pd.DataFrame(columns=["Chinese", "English", "Pinyin"])


     
def save_df_to_gsheet(
        gsheet_name, 
        wks_name,
        df_to_save,
        overwrite_mode = False
    ):
    sa = gspread.service_account()
    sh = sa.open(gsheet_name)
    wks = sh.worksheet(wks_name)

    if not overwrite_mode:
        existing = gd.get_as_dataframe(wks)
        df_to_save = pd.concat([existing, df_to_save])
        
    wks.batch_clear(["A:Q"])
    gd.set_with_dataframe(wks, df_to_save)


def format_gsheet(
        gsheet_name, 
        wks_name
    ):
    sa = gspread.service_account()
    sh = sa.open(gsheet_name)
    wks = sh.wks(wks_name)

    fmt = cellFormat(
        backgroundColor=color(0.6, 0.8, 0.9),
        textFormat=textFormat(bold=True, fontSize=15, foregroundColor=color(0, 0, 0.6)),
        horizontalAlignment='CENTER'
        )

    gf.format_cell_range(wks, 'A1:H1', fmt)

    fmt = cellFormat(
        textFormat=textFormat(fontSize=15),
        )

    gf.format_cell_range(wks, 'A2:A500', fmt)
    gf.format_cell_range(wks, 'E2:E500', fmt)
