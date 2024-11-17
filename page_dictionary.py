# Import packages
from dash import Dash, html, dash_table, dcc, callback, Output, Input
from main.translation import *
import pandas as pd
import dash_bootstrap_components as dbc


# Incorporate data
dict_path = "ChineseWords/ChineseWordList.csv"
dict_sheet_name = "Tua_List"
gsheet_name = "New Chinese Words"

df = load_dict(gsheet_mode=True, gsheet_name=gsheet_name, worksheet_name=dict_sheet_name)
word_date = df['Added Date'].drop_duplicates().sort_values().to_list()
word_cat = df['Word Category'].drop_duplicates().sort_values().to_list()
word_rarity = df['Word Rarity'].drop_duplicates().sort_values().to_list()


# Generate styles for the app
external_stylesheets = [dbc.themes.MATERIA]
app = Dash(__name__, external_stylesheets=external_stylesheets)

# Initialize the app
app = Dash()

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
    ], className="mb-5"),  # Space between filters and table
    html.Hr(),
    # Data table with additional margin and styling
    dbc.Row(dbc.Col(
        dash_table.DataTable(data=df.to_dict('records'), page_size=50, id='datatable'),
        width=12,
        className="shadow-lg p-3 mb-5 bg-white rounded"
    )),
], fluid=True)


# Add controls to build the interaction
@callback(
    Output(component_id='datatable', component_property='data'),
    [Input(component_id='date-dropdown', component_property='value'),
     Input(component_id='category-dropdown', component_property='value'),
     Input(component_id='rarity-dropdown', component_property='value')]
)
def slice_table(
    date_filter: str = None,
    category_filter: str = None, 
    rarity_filter: str = None
    ) -> pd.Series:
    out_table = df.copy()
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


# Run the app
if __name__ == '__main__':
    app.run(debug=True)