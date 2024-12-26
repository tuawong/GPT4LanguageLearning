# Import packages
import dash
from dash import Dash, html, dash_table, dcc, callback, Output, Input, State, callback_context
from main.translation import *
from main.quiz import QuizGenerator
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

quiz_generator = QuizGenerator(
    gsheet_name = gsheet_name,
    wks_name = dict_sheet_name
)

dash.register_page(__name__, path='/wordquiz', name='Word Quiz')

# App layout
layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            # Input box for number
            dbc.Card([
                dbc.CardBody([
                    html.B("Number of Words in Quiz"), 
                    dcc.Input(
                        id='quiz-word-num',
                        type='number',
                        value=10,
                        min=0,
                        placeholder=None,
                        style={'width': '100%', 'marginBottom': '10px'}  # Full width with margin below
                    ),
                    html.Div(id='number-output', style={'marginTop': '5px', 'color': 'gray'})  # To display input feedback
                ])
            ], className="mb-4 shadow-sm"),
        ], width=4),
    ]),
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
        dbc.Col([dbc.Button('Generate Quiz', id='gen-quiz-button', n_clicks=0, color='primary')]),
    ], className="mb-5"),  # Space between filters and table

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
                id='quiz-display'
            ),
            width=12,
            className="shadow-lg p-3 mb-5 bg-white rounded"
    )),
    dbc.Col([dbc.Button('Score Quiz', id='score-quiz-button', n_clicks=0, color='primary')]),
    html.Div(id='score-status', style={'marginTop': '20px', 'fontSize': '20px', 'fontWeight': 'bold'}),
], fluid=True)


@callback(
    [
        Output(component_id='quiz-display', component_property='data'),
        Output(component_id='quiz-display', component_property='columns'),
        Output('score-status', 'children'),
    ],
    [
        Input('gen-quiz-button', 'n_clicks'),
        Input('score-quiz-button', 'n_clicks'),
    ],
    [
        State('quiz-word-num', 'value'),
        State('date-dropdown', 'value'),
        State('category-dropdown', 'value'),
        State('rarity-dropdown', 'value'),
        State('quiz-display', 'data'),
    ],
)
def handle_quiz_buttons(n_quiz_clicks, n_score_clicks, num_words, date_filter, category_filter, rarity_filter, quiz_table_data):
    ctx = callback_context  # Determine which input triggered the callback

    # Default outputs
    display_data = []
    display_columns = []
    message = ""

    if not ctx.triggered:
        return display_data, display_columns, message

    # Identify the button that triggered the callback
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if button_id == 'gen-quiz-button' and n_quiz_clicks > 0:
        # Handle Quiz Generation
        if date_filter == 'All':
            date_filter = None
        if category_filter == 'All':
            category_filter = None
        if rarity_filter == 'All':
            rarity_filter = None

        quiz_df = quiz_generator.generate_pinyin_and_meaning_quiz(
            num_words=num_words,
            date_filter=date_filter,
            category_filter=category_filter,
            rarity_filter=rarity_filter,
        )
        display_df = quiz_df.drop(columns=['Word Id'])

        display_data = display_df.to_dict('records')
        display_columns = [{"name": i, "id": i} for i in display_df.columns]
        message = "Quiz Generated!"

    elif button_id == 'score-quiz-button' and n_score_clicks > 0:
        # Handle Scoring the Quiz
        if quiz_table_data:  # Ensure there is data to score
            quiz_df = pd.DataFrame(quiz_table_data)  # Convert current table data to DataFrame
            quiz_result = quiz_generator.evaluate_pinyin_and_meaning_quiz(
                pinyin_answer=quiz_df['Pinyin'],
                meaning_answer=quiz_df['Meaning'],
            )
            #print(quiz_df['Meaning'])
            #print(quiz_result.head())
            display_data = quiz_result.to_dict('records')
            display_columns = [{"name": i, "id": i} for i in quiz_result.columns]
            message = "Quiz Scored!"

            quiz_generator.update_quiz_score(
                gsheet_name = gsheet_name, 
                wks_name = 'Tua_List'
            )

            quiz_generator.output_quiz_log(
                gsheet_name = gsheet_name, 
                wks_name = 'QuizLog'
            )

            quiz_generator.quiz_result = None  # Reset quiz result after scoring

    return display_data, display_columns, message