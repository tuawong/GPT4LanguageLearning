# Import packages
import dash
from dash import Dash, html, dash_table, dcc, callback, Output, Input, State, ctx
from main.translation import *
import pandas as pd
import dash_bootstrap_components as dbc

import main.Constants as Constants
from database import engine, ensure_views_from_files
from main.sql import load_dict, sql_delete_word_dict, sql_patch_worddict_rows

ensure_views_from_files()
orig_df = load_dict()
orig_df = orig_df.sort_index(ascending=False)

# Don't really need to show Pinyin Simplified column
orig_df = orig_df.drop(columns=['Pinyin Simplified'])
orig_df['Pinyin Errors'] = orig_df['Quiz Attempts'] - orig_df['Num Pinyin Correct']
orig_df['Meaning Errors'] = orig_df['Quiz Attempts'] - orig_df['Num Meaning Correct']

# Move Last Quiz to the final column
cols = [c for c in orig_df.columns if c != 'Last Quiz'] + ['Last Quiz']
orig_df = orig_df[cols]

word_date = orig_df['Added Date'].drop_duplicates().sort_values().to_list()
word_cat = orig_df['Word Category'].drop_duplicates().sort_values().to_list()
word_rarity = orig_df['Word Rarity'].drop_duplicates().sort_values().to_list()

_EDITABLE_COLS = {'Pinyin', 'Meaning', 'Word Category', 'Word Rarity', 'Type',
                  'Sentence', 'Sentence Pinyin', 'Sentence Meaning'}
dict_columns = [{'name': col, 'id': col, 'editable': col in _EDITABLE_COLS}
                for col in orig_df.columns]

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
        ], width=3),

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
        ], width=3),

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
        ], width=3),

        #Word Filter with space in between
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.B("Word Filter"),
                    dcc.Input(
                        id= "word-dict-filter",
                        type='text',
                        value='',
                        placeholder=None,
                        style={'width': '100%', 'marginBottom': '10px'}  # Full width with margin below
                    ),
                    ])
                ], className="mb-4 shadow-sm")
        ], width=3, className="mb-5"),

        # Button to reload table
        dbc.Row([
            dbc.Col([
                dbc.Button('Reload Table', id='reload-button', n_clicks=0, color='primary', className='me-2'),
                dbc.Button('Delete Selected', id='dict-delete-button', n_clicks=0, color='danger', className='me-2'),
                dbc.Button('Save Changes', id='dict-save-button', n_clicks=0, color='success'),
            ], width='auto'),
        ]),
    ], className="mb-5"),  # Space between filters and table

    html.Hr(),
    # Delete status
    html.Div(id='dict-delete-status', style={'color': '#6c757d', 'marginBottom': '8px'}),
    # Data table with additional margin and styling
    dcc.Store(id="table-data-store"),
    dbc.Row(dbc.Col(
        dash_table.DataTable(
                data=orig_df.to_dict('records'),
                columns=dict_columns,
                sort_action="native",  # Enable sorting
                #filter_action="native",  # Enable filtering
                editable=True,  # Enable cell editing
                row_selectable='multi',
                selected_rows=[],
                style_table={
                    'overflowX': 'auto',
                    'width': '100%',  
                },  
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
                style_data_conditional=[
                    {
                        'if': {'state': 'selected'},
                        'backgroundColor': '#cfe2ff',
                        'border': '1px solid #0d6efd',
                    }
                ],
                page_size=15, 
                id='dict-display'
            ),
            width=12,
            className="shadow-lg p-3 mb-5 bg-white rounded"
    )),
], fluid=True)

@callback(
    Output(component_id='table-data-store', component_property='data'),
    Output('dict-display', 'selected_rows'),
    Output('dict-delete-status', 'children'),
    Input('reload-button', 'n_clicks'),
    Input('dict-delete-button', 'n_clicks'),
    Input('dict-save-button', 'n_clicks'),
    State('dict-display', 'selected_rows'),
    State('dict-display', 'data'),
)
def reload_table(reload_clicks, delete_clicks, save_clicks, selected_rows, table_data):
    triggered = ctx.triggered_id

    if triggered == 'dict-save-button':
        if not table_data:
            return dash.no_update, dash.no_update, "Nothing to save."
        message = sql_patch_worddict_rows(table_data)
        return dash.no_update, dash.no_update, message

    if triggered == 'dict-delete-button':
        if not selected_rows or not table_data:
            return dash.no_update, [], "No rows selected for deletion."
        word_ids = [
            table_data[i]['Word Id']
            for i in selected_rows
            if table_data[i].get('Word Id')
        ]
        message = sql_delete_word_dict(word_ids)
        df = load_dict()
        df = df.sort_index(ascending=False)
        df = df.drop(columns=['Pinyin Simplified'])
        df['Pinyin Errors'] = df['Quiz Attempts'] - df['Num Pinyin Correct']
        df['Meaning Errors'] = df['Quiz Attempts'] - df['Num Meaning Correct']
        cols = [c for c in df.columns if c != 'Last Quiz'] + ['Last Quiz']
        df = df[cols]
        return df.to_dict('records'), [], message

    if reload_clicks and reload_clicks > 0:
        df = load_dict()
        df = df.sort_index(ascending=False)
        df = df.drop(columns=['Pinyin Simplified'])
        df['Pinyin Errors'] = df['Quiz Attempts'] - df['Num Pinyin Correct']
        df['Meaning Errors'] = df['Quiz Attempts'] - df['Num Meaning Correct']
        cols = [c for c in df.columns if c != 'Last Quiz'] + ['Last Quiz']
        df = df[cols]
        return df.to_dict('records'), [], ""
    else:
        return orig_df.to_dict('records'), [], ""

# Add controls to build the interaction
@callback(
    Output(component_id='dict-display', component_property='data'),
    [Input(component_id='table-data-store', component_property='data'),
     Input(component_id='date-dropdown', component_property='value'),
     Input(component_id='category-dropdown', component_property='value'),
     Input(component_id='rarity-dropdown', component_property='value'),
     Input(component_id='word-dict-filter', component_property='value')
     ]
)
def slice_table(
    table_data: pd.DataFrame,
    date_filter: str = None,
    category_filter: str = None, 
    rarity_filter: str = None,
    word_filter: str = None
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

    if word_filter is not None and word_filter != '':
        if type(word_filter) == str:
            out_table = out_table.loc[out_table.Word.str.contains(word_filter)]

    return out_table.to_dict('records')


