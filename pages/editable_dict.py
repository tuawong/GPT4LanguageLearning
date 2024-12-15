import dash
from dash import Dash, dash_table, dcc, html, Input, Output, callback
from main.translation import *
import pandas as pd

dash.register_page(__name__, path='/editdict')

# Incorporate data
dict_sheet_name = "Tua_List"
gsheet_name = "New Chinese Words"

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
