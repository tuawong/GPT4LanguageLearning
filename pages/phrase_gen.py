# Import packages
import dash
from dash import Dash, html, dash_table, dcc, callback, Output, Input, State, callback_context
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
from main.phrase_generator import PhraseGenerationPipeline
from main.dash_utils import create_tabs
from main.sql import load_phrase_dict
import main.Constants as Constants


# Incorporate data
phrasesheet_name = Constants.PHRASE_SHEET_NAME
gsheet_name = Constants.SHEET_NAME

#df = load_dict(gsheet_mode=True, gsheet_name=gsheet_name, worksheet_name=phrasesheet_name)
df = pd.DataFrame()

# Generate styles for the app
dash.register_page(__name__, path='/phrasegen', name='Phrase Generator')

phrase_generator = PhraseGenerationPipeline(
    gsheet_name = gsheet_name,
    worksheet_name = phrasesheet_name
)


phrase_dict = load_phrase_dict()
existing_phrases = phrase_dict['Line'].drop_duplicates().values.tolist()

# App layout
layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.B("Situation"), 
                    dcc.Input(
                        id= "phrase-input-situation",
                        type='text',
                        value='',
                        placeholder=None,
                        style={'width': '100%', 'marginBottom': '10px'}  # Full width with margin below
                    ),
                    html.Div(id='number-output', style={'marginTop': '5px', 'color': 'gray'})  # To display input feedback
                ])
            ], className="mb-4 shadow-sm"),
        ], width=3),
        dbc.Col([
            # Input box for number
            dbc.Card([
                dbc.CardBody([
                    html.B("Number of Phrase to Gen"), 
                    dcc.Input(
                        id= "phrase-num",
                        type='number',
                        value=5,
                        min=0,
                        placeholder=None,
                        style={'width': '100%', 'marginBottom': '10px'}  # Full width with margin below
                    ),
                    html.Div(id='number-output', style={'marginTop': '5px', 'color': 'gray'})  # To display input feedback
                ])
            ], className="mb-4 shadow-sm"),
        ], width=3),
        dbc.Col([
            dbc.ButtonGroup([
                dbc.Button('Generate Phrase', id='gen-phrase-button', n_clicks=0, color='primary'),
            ])
        ], width="auto", className="d-flex align-items-center"),
    ], className="mb-3"),
    
    dbc.Row([
        dbc.Col([
            # Input box for number
            dbc.Card([
                dbc.CardBody([
                    html.B("Input Phrase"), 
                    dcc.Input(
                        id= "phrase-input",
                        type='text',
                        value='',
                        placeholder=None,
                        style={'width': '100%', 'marginBottom': '10px'}  # Full width with margin below
                    ),
                    html.Div(id='number-output', style={'marginTop': '5px', 'color': 'gray'})  # To display input feedback
                ])
            ], className="mb-4 shadow-sm"),
        ], width=3),
        dbc.Col([
            dbc.ButtonGroup([
                dbc.Button('Generate Response', id='gen-response-button', n_clicks=0, color='secondary'),
            ])
        ], width="auto", className="d-flex align-items-center"),
    ], className="mb-3"),

    dbc.Row([
        dbc.Col([
            # Input box for number
            dbc.Card([
                dbc.CardBody([
                    html.B("Input Translation"), 
                    dcc.Input(
                        id= "translation-input",
                        type='text',
                        value='',
                        placeholder=None,
                        style={'width': '100%', 'marginBottom': '10px'}  # Full width with margin below
                    ),
                    html.Div(id='number-output', style={'marginTop': '5px', 'color': 'gray'})  # To display input feedback
                ])
            ], className="mb-4 shadow-sm"),
        ], width=3),
        dbc.Col([
            dbc.ButtonGroup([
                dbc.Button('Generate Translation', id='gen-translation-button', n_clicks=0, color='primary'),
            ])
        ], width="auto", className="d-flex align-items-center"),
    ], className="mb-3"),
    
    
    # Filter dropdowns with space in between
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.B("Complexity"),
                    dcc.Dropdown(
                        options=[{'label': option, 'value': option} for option in ['Low', 'Medium', 'High']],
                        value='All',
                        id= "phrase-complexity",
                    )
                ])
            ], className="mb-4 shadow-sm")
        ], width=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.B("Tone"),
                    dcc.Dropdown(
                        options=[{'label': option, 'value': option} for option in ['Polite', 'Casual']],
                        value='All',
                        id= "phrase-tone",
                    )
                ])
            ], className="mb-4 shadow-sm")
        ], width=3),
    ], className="mb-5"),

    html.Hr(),
    # Data table with additional margin and styling
    dbc.Row(dbc.Col(
        html.Div("Preview Table", 
                className="text-center mb-5", 
                style={"font-size": "1.25rem", "color": "#6c757d"}),  # Adjust font size and color
        className="d-flex justify-content-center"
    )),
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
                id='phrase-datatable',
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
                dbc.Button('Update Table', id='phrase-update-button', n_clicks=0, color='primary'),
                dbc.Button('Reset Table', id='phrase-reset-button', n_clicks=0, color='secondary'),
            ]),
            html.Div(id='phrase-update-status', style={'marginTop': '20px', 'fontSize': '20px', 'fontWeight': 'bold'}),
            html.Div(id='phrase-clear-status', style={'marginTop': '20px', 'fontSize': '20px', 'fontWeight': 'bold'}),
        ])
        ))
    ],
    fluid=True
)



# Callback to update output text on button click
@callback(
    [Output(component_id='phrase-datatable', component_property='data'),
    Output(component_id='phrase-datatable', component_property='columns')],
    Input('gen-phrase-button', 'n_clicks'),  
    Input('gen-response-button', 'n_clicks'),  
    Input('gen-translation-button', 'n_clicks'),  
    State('phrase-input-situation', 'value'),            
    State('phrase-num', 'value'),            
    State('phrase-complexity', 'value'),   
    State('phrase-tone', 'value'),
    State('phrase-input', 'value'),
    State('translation-input', 'value'),
)
def run_phrase_gen(n_clicks_gen, n_clicks_response, n_clicks_translation, situation, num_phrases, complexity, tone, input_phrases, input_translation):
    ctx = callback_context  # Get the context of which button was clicked

    button_id = ctx.triggered[0]["prop_id"].split(".")[0]  # Get the ID of the clicked button

    if button_id == "gen-phrase-button":
        phrase_generator.phrase_generation_module(situation, num_phrases, complexity, tone, existing_phrases=existing_phrases, translation_model = 'gpt-4o', temp=0.7)

    if button_id == "gen-response-button":
        phrase_generator.phrase_response_module(input_phrases, complexity, tone, translation_model = 'gpt-4o', temp=0.7)

    if button_id == "gen-translation-button":
        phrase_generator.phrase_translate_module(input_translation, complexity, tone, translation_model = 'gpt-4o', temp=0.7)

    return phrase_generator.new_phrase_df.to_dict('records'), [{"name": i, "id": i} for i in phrase_generator.new_phrase_df.columns]


@callback(
    Output('phrase-update-status', 'children'),
    Input('phrase-update-button', 'n_clicks'),
    State('phrase-datatable', 'data')
)
def gen_update_output(n_clicks, data_to_update):
    if n_clicks > 0 and hasattr(phrase_generator, 'new_phrase_df'):
        updated_table_df = pd.DataFrame(data_to_update)
        if len(updated_table_df)> 0:
            message = phrase_generator.update_module(df=updated_table_df)
            phrase_generator.clear_new_phrases()
            return message
        else:
            return "Please first generate phrase before update."
    return ""


@callback(
    Output('phrase-clear-status', 'children'),
    Input('phrase-reset-button', 'n_clicks')   
)
def gen_clear_output(n_clicks):
    if n_clicks > 0 and hasattr(phrase_generator, 'new_phrase_df'):
        if len(phrase_generator.new_phrase_df)> 0:
            phrase_generator.clear_new_phrases()
            return "Reset successful."
    return ""
