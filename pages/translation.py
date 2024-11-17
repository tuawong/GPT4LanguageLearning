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

from main.translation import TranslationPipeline, load_dict

# Incorporate data
dict_sheet_name = "Tua_List"
gsheet_name = "New Chinese Words"
translator_pipe = TranslationPipeline(gsheet_name=gsheet_name, worksheet_name=dict_sheet_name)

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
                    html.Label('Please Enter Text for Translation Here', style={'marginRight': '10px', "font-size": "1rem", "color": "#6c757d"}),
                    dcc.Input(id='word-list', type='text', placeholder='Enter some text', style={'marginRight': '10px'}),
                    dbc.Button('Submit', id='submit-button', n_clicks=0)
                ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '20px'}),
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
                        data=df.to_dict('records'), 
                        page_size=50, 
                        sort_action="native",
                        editable=True,
                        id='datatable'
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
                ])
            )),
        ]
        , fluid=True
    )

# Callback to update output text on button click
@callback(
    Output(component_id='datatable', component_property='data'),
    Input('submit-button', 'n_clicks'),     
    State('word-list', 'value')           
)
def run_translation(n_clicks, word_list):
    if n_clicks > 0 and word_list:
        translator_pipe.translation_module(word_list, temp=0.7, replace_new_words=False)
        return translator_pipe.new_words_df.to_dict('records')
    return df.to_dict('records')

@callback(
    Output('update-status', 'children'),
    Input('update-button', 'n_clicks')   
)
def update_output(n_clicks):
    if n_clicks > 0 and hasattr(translator_pipe, 'new_words_df'):
        if len(translator_pipe.new_words_df)> 0:
            message = translator_pipe.update_module(overwrite_mode=True)
            translator_pipe.clear_new_words()
            return message
        else:
            return "Please add words to be translated and click Submit."
    return ""
