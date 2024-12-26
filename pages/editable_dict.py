import dash
from dash import Dash, dash_table, dcc, html, Input, Output, callback
from main.translation import *
import pandas as pd
import main.Constants as Constants

dash.register_page(__name__, path='/editdict')

# Incorporate data
dict_sheet_name = Constants.DICT_SHEET_NAME
gsheet_name = Constants.SHEET_NAME

orig_df = load_dict(gsheet_mode=True, gsheet_name=gsheet_name, worksheet_name=dict_sheet_name)
orig_df = orig_df.head(12)


layout = html.Div([
    dash_table.DataTable(
        id='table-editing-simple',
        columns=(
            [{'id': p, 'name': p} for p in orig_df.columns]
        ),
        data=orig_df.to_dict('records'),
        editable=True
    )
])
