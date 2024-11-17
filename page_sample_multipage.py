from dash import Dash, dcc, html, callback, Output, Input, State
import dash_bootstrap_components as dbc

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Define the app layout with links to different pages
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),  # Tracks the URL
    dbc.NavbarSimple([
        dbc.NavItem(dcc.Link('Home', href='/', className="nav-link")),
        dbc.NavItem(dcc.Link('Testing Submit Box', href='/page-1', className="nav-link")),
        dbc.NavItem(dcc.Link('Page 2', href='/page-2', className="nav-link"))
    ], brand="Multi-Page Dash App", color="primary", dark=True, className="mb-4"),
    
    # The layout for displaying each page's content
    html.Div(id='page-content')
])

# Home page layout with text input and submit button
home_layout = html.Div([
    html.H2("Home Page"),
    html.P("Welcome to the Home Page!")
])

# Testing Submit Box layout
page_1_layout = html.Div([
    html.H2("Testing Submit Box"),
    html.P("Welcome to Testing Submit Box!"),
    
    # Text input and submit button
    html.Div([
        dcc.Input(id='text-input', type='text', placeholder='Enter some text', style={'marginRight': '10px'}),
        html.Button('Submit', id='submit-button', n_clicks=0)
    ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '20px'}),
    
    # Output display for the submitted text
    html.Div(id='output-text', style={'marginTop': '20px', 'fontSize': '20px', 'fontWeight': 'bold'})
])

# Page 2 layout
page_2_layout = html.Div([
    html.H2("Page 2"),
    html.P("Welcome to Page 2!")
])

# Callback to update page content based on URL
@callback(Output('page-content', 'children'), [Input('url', 'pathname')])
def display_page(pathname):
    if pathname == '/page-1':
        return page_1_layout
    elif pathname == '/page-2':
        return page_2_layout
    else:
        return home_layout  # Default to home page

# Callback to update output text on button click
@callback(
    Output('output-text', 'children'),
    Input('submit-button', 'n_clicks'),     # Triggered by button click
    State('text-input', 'value')            # Text input's current value is captured as State
)
def update_output(n_clicks, input_value):
    if n_clicks > 0 and input_value:
        return f'You entered: {input_value}'
    return "Please enter text and click Submit."

if __name__ == "__main__":
    app.run_server(debug=True)
