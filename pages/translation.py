# Import packages
import dash
from dash import Dash, html, dash_table, dcc, callback, Output, Input, State
from main.translation import *
import pandas as pd
import dash_bootstrap_components as dbc
from dotenv import load_dotenv
import os
import sys

# Load environment variables from .env file
# So we can import from upper folders
#load_dotenv()
#pythonpaths = os.getenv("PYTHONPATH", "").split(os.pathsep)
#for path in pythonpaths:
#    if path and path not in sys.path:
#        sys.path.insert(0, path)

from main.gsheets import load_gsheet_dict
from main.translation import TranslationPipeline
import main.Constants as Constants

# Incorporate data
#dict_sheet_name = Constants.DICT_SHEET_NAME
#gsheet_name = Constants.SHEET_NAME
#translator_pipe = TranslationPipeline(gsheet_name=gsheet_name, worksheet_name=dict_sheet_name)
translator_pipe = TranslationPipeline()

#df = load_dict(gsheet_mode=True, gsheet_name=gsheet_name, worksheet_name=dict_sheet_name)
df = pd.DataFrame()

# Generate styles for the app
dash.register_page(__name__, path='/translation', name='Translation')


# App layout
layout = dbc.Container(
        [
            # Text input and submit button
            dbc.Row(dbc.Col(
                html.Div([
                    html.Label('Enter Words for Translation (one per row)',
                               style={"font-size": "1rem", "color": "#6c757d", "marginBottom": "8px"}),
                    dash_table.DataTable(
                        id='word-input-table',
                        columns=[{'id': 'word', 'name': 'Word', 'editable': True}],
                        data=[{'word': ''} for _ in range(10)],
                        editable=True,
                        row_deletable=True,
                        style_table={'height': '300px', 'overflowY': 'auto', 'width': '320px'},
                        style_cell={'textAlign': 'left', 'padding': '8px', 'fontFamily': 'Arial'},
                        style_header={'fontWeight': 'bold', 'backgroundColor': '#f8f9fa'},
                    ),
                    dbc.ButtonGroup([
                        dbc.Button('+ Add Row', id='add-row-button', n_clicks=0, color='light', size='sm', style={'marginTop': '8px'}),
                        dbc.Button('Submit', id='submit-button', n_clicks=0, size='sm', style={'marginTop': '8px'}),
                    ])
                ], style={'display': 'flex', 'flexDirection': 'column', 'alignItems': 'flex-start', 'marginBottom': '20px'}),
                className="d-flex justify-content-center"
            )),
            html.Hr(),
            
            dbc.Row(dbc.Col(
                html.Div("Preview Table", 
                        className="text-center mb-5", 
                        style={"font-size": "1.25rem", "color": "#6c757d"}),  # Adjust font size and color
                className="d-flex justify-content-center"
            )),
            
            # Data table with additional margin and styling
            dbc.Row(
                dbc.Col(
                    dash_table.DataTable(
                        #columns=(
                        #    [{'id': p, 'name': p} for p in df.columns]
                        #),
                        data=df.to_dict('records'), 
                        page_size=50, 
                        sort_action="native",
                        editable=True,
                        row_deletable=True,
                        id='vocab-datatable',
                        style_cell={
                            "textAlign": "center",  # Align text to the center
                            "padding": "10px",      # Add padding to cells
                            "fontFamily": "Arial",  # Set font
                        },
                ),
                width=12,
                className="shadow-lg p-3 mb-5 bg-white rounded"
            )),
            dbc.Row(dbc.Col(
                html.Div([
                    dbc.ButtonGroup([
                        dbc.Button('Update Table', id='update-button', n_clicks=0, color='primary'),
                        dbc.Button('Reset Table', id='reset-button', n_clicks=0, color='secondary'),
                    ]),
                    html.Div(id='update-status', style={'marginTop': '20px', 'fontSize': '20px', 'fontWeight': 'bold'}),
                    html.Div(id='clear-status', style={'marginTop': '20px', 'fontSize': '20px', 'fontWeight': 'bold'}),
                ])
            )),
        ]
        , fluid=True
    )

@callback(
    Output('word-input-table', 'data'),
    Input('add-row-button', 'n_clicks'),
    State('word-input-table', 'data'),
    prevent_initial_call=True
)
def add_row(n_clicks, current_data):
    current_data.append({'word': ''})
    return current_data


# Callback to update output text on button click
@callback(
    [Output(component_id='vocab-datatable', component_property='data'),
    Output(component_id='vocab-datatable', component_property='columns')],
    Input('submit-button', 'n_clicks'),
    State('word-input-table', 'data')
)
def run_translation(n_clicks, word_table_data):
    if n_clicks > 0 and word_table_data:
        words = [row['word'] for row in word_table_data if row.get('word', '').strip()]
        if words:
            word_list = ', '.join(words)
            translator_pipe.translation_module(word_list, translation_model="gpt-5-mini", rarity_model="gpt-5-mini", temp=1, replace_new_words=False)
    return translator_pipe.new_words_df.to_dict('records'), [{"name": i, "id": i} for i in translator_pipe.new_words_df.columns]


@callback(
    Output('update-status', 'children'),
    Input('update-button', 'n_clicks'),
    State('vocab-datatable', 'data')
)
def update_output(n_clicks, data_to_update):
    if n_clicks > 0 and hasattr(translator_pipe, 'new_words_df'):
        updated_table_df = pd.DataFrame(data_to_update)
        if len(updated_table_df)> 0:
            message = translator_pipe.update_module(df=updated_table_df, overwrite_mode=True)
            translator_pipe.clear_new_words()
            return message
        else:
            return "Please add words to be translated and click Submit."
    return ""


@callback(
    Output('clear-status', 'children'),
    Input('reset-button', 'n_clicks')   
)
def clear_output(n_clicks):
    if n_clicks > 0 and hasattr(translator_pipe, 'new_words_df'):
        if len(translator_pipe.new_words_df)> 0:
            translator_pipe.clear_new_words()
            return "Reset successful."
    return ""
