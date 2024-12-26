# Import packages
import dash
from dash import Dash, html, dash_table, dcc, callback, Output, Input
from main.translation import *
import pandas as pd
import dash_bootstrap_components as dbc

import main.Constants as Constants

# Incorporate data
dict_sheet_name = Constants.DICT_SHEET_NAME
gsheet_name = Constants.SHEET_NAME

orig_df = load_dict(gsheet_mode=True, gsheet_name=gsheet_name, worksheet_name=dict_sheet_name)
word_date = orig_df['Added Date'].drop_duplicates().sort_values().to_list()
word_cat = orig_df['Word Category'].drop_duplicates().sort_values().to_list()
word_rarity = orig_df['Word Rarity'].drop_duplicates().sort_values().to_list()


dash.register_page(__name__, path='/dictionary')

# App layout
layout = dbc.Container([
    # Filter dropdowns with space in between
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.B("Date Filter"),
                    dcc.Dropdown(
                        options=[{'label': option, 'value': option} for option in ['All'] + word_date],
                        value='All',
                        id='date-dropdown',
                    )
                ])
            ], className="mb-4 shadow-sm")
        ], width=4),

        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.B("Category Filter"),
                    dcc.Dropdown(
                        options=[{'label': option, 'value': option} for option in ['All'] + word_cat],
                        value='All',
                        id='category-dropdown',
                    )
                ])
            ], className="mb-4 shadow-sm")
        ], width=4),

        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.B("Rarity Filter"),
                    dcc.Dropdown(
                        options=[{'label': option, 'value': option} for option in ['All'] + word_rarity],
                        value='All',
                        id='rarity-dropdown',
                    )
                ])
            ], className="mb-4 shadow-sm")
        ], width=4),
        dbc.Col([dbc.Button('Reload Table', id='reload-button', n_clicks=0, color='primary')]),
    ], className="mb-5"),  # Space between filters and table

    html.Hr(),
    # Data table with additional margin and styling
    dcc.Store(id="table-data-store"),
    dbc.Row(dbc.Col(
        dash_table.DataTable(
                data=orig_df.to_dict('records'),
                sort_action="native",  # Enable sorting
                #filter_action="native",  # Enable filtering
                editable=True,  # Enable cell editing
                style_table={'overflowX': 'auto'},  # Responsive styling
                style_cell={
                    "textAlign": "center",  # Align text to the center
                    "padding": "10px",      # Add padding to cells
                    "fontFamily": "Arial",  # Set font
                },
                style_header={
                    'backgroundColor': '#f8f9fa',  # Light gray header background
                    'fontWeight': 'bold'
                },
                style_data={
                    'backgroundColor': '#ffffff',  # White background for data
                    'color': '#212529'  # Dark text color
                },
                page_size=50, 
                id='dict-display'
            ),
            width=12,
            className="shadow-lg p-3 mb-5 bg-white rounded"
    )),
], fluid=True)

@callback(
    Output(component_id='table-data-store', component_property='data'),
    Input('reload-button', 'n_clicks')
)
def reload_table(n_clicks):
    if n_clicks > 0:
        df = load_dict(gsheet_mode=True, gsheet_name=gsheet_name, worksheet_name=dict_sheet_name)
        return df.to_dict('records')
    else:
        return orig_df.to_dict('records')

# Add controls to build the interaction
@callback(
    Output(component_id='dict-display', component_property='data'),
    [Input(component_id='table-data-store', component_property='data'),
     Input(component_id='date-dropdown', component_property='value'),
     Input(component_id='category-dropdown', component_property='value'),
     Input(component_id='rarity-dropdown', component_property='value')]
)
def slice_table(
    table_data: pd.DataFrame,
    date_filter: str = None,
    category_filter: str = None, 
    rarity_filter: str = None
    ) -> pd.Series:
    out_table = pd.DataFrame(table_data)
    if date_filter!= 'All':
        out_table = out_table[out_table['Added Date'] >= date_filter]

    if category_filter != 'All':
        if type(category_filter) == str:
            category_filter = [category_filter]
            out_table = out_table[out_table['Word Category'].isin(category_filter)]

    if rarity_filter != 'All':
        if type(rarity_filter) == str:
            rarity_filter = [rarity_filter]
            out_table = out_table[out_table['Word Rarity'].isin(rarity_filter)]

    return out_table.to_dict('records')

