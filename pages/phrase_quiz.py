# Import packages
import dash
from dash import Dash, html, dash_table, dcc, callback, Output, Input, State, callback_context
from main.translation import *
from main.chat_eval import ResponseQuizGenerator
import pandas as pd
import dash_bootstrap_components as dbc

import main.Constants as Constants

# Incorporate data
dict_sheet_name = Constants.RESPONSE_LOG_SHEET_NAME
gsheet_name = Constants.SHEET_NAME

response_quiz_generator = ResponseQuizGenerator(
    gsheet_name = gsheet_name,
    wks_name = dict_sheet_name
)

dash.register_page(__name__, path='/responsequiz', name='Response Quiz')

# App layout
layout = dbc.Container([
   dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.B("Situation"), 
                    dcc.Input(
                        id= "phrase-quiz-situation",
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
                        id= "phrase-quiz-num",
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
    ]),

    # Filter dropdowns with space in between
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.B("Complexity"),
                    dcc.Dropdown(
                        options=[{'label': option, 'value': option} for option in ['Low', 'Medium', 'High']],
                        value='All',
                        id= "phrase-quiz-complexity",
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
                        id= "phrase-quiz-tone",
                    )
                ])
            ], className="mb-4 shadow-sm")
        ], width=3),
    ], className="mb-5"),

    dbc.Row([
        dbc.Col([
            dbc.ButtonGroup([
                dbc.Button('Generate Phrase', id='gen-phrase-quiz-button', n_clicks=0, color='primary'),
            ])
        ], width=0.8),
    ]),

    html.Hr(),
    # Data table with additional margin and styling
    dbc.Row(dbc.Col(
        dash_table.DataTable(
                #data=orig_df.to_dict('records'),
                #sort_action="native",  # Enable sorting
                #filter_action="native",  # Enable filtering
                editable=True,  # Enable cell editing
                style_table={'overflowX': 'auto'},  # Responsive styling
                style_cell={
                    "fontSize": "24px", # Set font size
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
                id='phrase-quiz-display'
            ),
            width=12,
            className="shadow-lg p-3 mb-5 bg-white rounded"
    )),
    dbc.Col([dbc.Button('Score Quiz', id='score-phrase-quiz-button', n_clicks=0, color='primary')]),
    html.Div(id='response-score-status', style={'marginTop': '20px', 'fontSize': '20px', 'fontWeight': 'bold'}),
], fluid=True)


@callback(
    [
        Output(component_id='phrase-quiz-display', component_property='data'),
        Output(component_id='phrase-quiz-display', component_property='columns'),
        Output('response-score-status', 'children'),
    ],
    [
        Input('gen-phrase-quiz-button', 'n_clicks'),
        Input('score-phrase-quiz-button', 'n_clicks'),
    ],
    [
        State('phrase-quiz-num', 'value'),
        State('phrase-quiz-situation', 'value'),
        State('phrase-quiz-complexity', 'value'),
        State('phrase-quiz-tone', 'value'),
        State('phrase-quiz-display', 'data'),
    ],
)
def handle_quiz_buttons(n_quiz_clicks, n_score_clicks, num_phrases, situation, complexity, tone, quiz_table_data):
    ctx = callback_context  # Determine which input triggered the callback

    # Default outputs
    display_data = []
    display_columns = []
    message = ""

    if not ctx.triggered:
        return display_data, display_columns, message

    # Identify the button that triggered the callback
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if button_id == 'gen-phrase-quiz-button' and n_quiz_clicks > 0:
        response_quiz_generator.generate_response_quiz(
            situation = situation,
            num_phrases = num_phrases,
            complexity = complexity,
            tone = tone,
            temp = 0.7,
            model = "gpt-4o-mini"
        )

        display_df = response_quiz_generator.phrase_df
        display_data = display_df.to_dict('records')
        display_columns = [{"name": i, "id": i} for i in display_df.columns]
        message = "Quiz Generated!"

    elif button_id == 'score-phrase-quiz-button' and n_score_clicks > 0:
        # Handle Scoring the Quiz
        if quiz_table_data: 
            quiz_df = pd.DataFrame(quiz_table_data)  
            quiz_result = response_quiz_generator.evaluate_response(eval_df = quiz_df)

            display_data = quiz_result.to_dict('records')
            display_columns = [{"name": i, "id": i} for i in quiz_result.columns]
            message = "Quiz Scored!"

            response_quiz_generator.output_quiz_log()  # Export the response log to Google Sheets
            # Reset quiz result after scoring
            response_quiz_generator.eval_df = None
            response_quiz_generator.phrase_df = None  

    return display_data, display_columns, message