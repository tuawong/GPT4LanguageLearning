# Import packages
from dash import Dash, html, dash_table, dcc, callback, Output, Input, State
from main.translation import *
import pandas as pd
import dash_bootstrap_components as dbc
from dotenv import load_dotenv
import os
import sys

# Load environment variables from .env file
# So we can import from upper folders
load_dotenv()
pythonpaths = os.getenv("PYTHONPATH", "").split(os.pathsep)
for path in pythonpaths:
    if path and path not in sys.path:
        sys.path.insert(0, path)

from main.translation import TranslationPipeline, load_dict

# Incorporate data
dict_sheet_name = "Tua_List"
gsheet_name = "New Chinese Words"
translator_pipe = TranslationPipeline(gsheet_name=gsheet_name, worksheet_name=dict_sheet_name)

#df = load_dict(gsheet_mode=True, gsheet_name=gsheet_name, worksheet_name=dict_sheet_name)
df = pd.DataFrame()

# Generate styles for the app
external_stylesheets = [dbc.themes.MATERIA]
app = Dash(__name__, external_stylesheets=external_stylesheets)


# App layout
app.layout = dbc.Container([
    # Page title
    dbc.Row(dbc.Col(html.H1("Chinese Word Dictionary", className="text-center mb-4"), className="d-flex justify-content-center")),
    
    # Centered and smaller subtitle with extra margin
    dbc.Row(dbc.Col(
        html.Div("My Personal Chinese Word Repository.", 
                 className="text-center mb-5", 
                 style={"font-size": "1.25rem", "color": "#6c757d"}),  # Adjust font size and color
        className="d-flex justify-content-center"
    )),
    html.Hr(),

    # Text input and submit button
    html.Div([
        dcc.Input(id='word-list', type='text', placeholder='Enter some text', style={'marginRight': '10px'}),
        html.Button('Submit', id='submit-button', n_clicks=0)
    ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '20px'}),
    html.Div(id='output-text', style={'marginTop': '20px', 'fontSize': '20px', 'fontWeight': 'bold'}),
    html.Hr(),
    
    dbc.Row(dbc.Col(
        html.Div("Preview Table", 
                 className="text-center mb-5", 
                 style={"font-size": "1.25rem", "color": "#6c757d"}),  # Adjust font size and color
        className="d-flex justify-content-center"
    )),
    
    # Data table with additional margin and styling
    dbc.Row(dbc.Col(
        dash_table.DataTable(data=df.to_dict('records'), page_size=50, id='datatable'),
        width=12,
        className="shadow-lg p-3 mb-5 bg-white rounded"
    )),
], fluid=True)

# Callback to update output text on button click
@callback(
    [Output('output-text', 'children'),
     Output(component_id='datatable', component_property='data')],
    Input('submit-button', 'n_clicks'),     # Triggered by button click
    State('word-list', 'value')            # Text input's current value is captured as State
)
def update_output(n_clicks, word_list):
    if n_clicks > 0 and word_list:
        message = translator_pipe.run_translation_pipeline(word_list=word_list, temp=0.7, overwrite_mode=True)
        return message, translator_pipe.new_words_df.to_dict('records')
    return "Please enter text and click Submit.", df.to_dict('records')

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)