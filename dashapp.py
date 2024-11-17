import dash
from dash import Dash, html, dcc
import dash_bootstrap_components as dbc

external_stylesheets = [dbc.themes.MATERIA]
app = Dash(__name__, use_pages=True, external_stylesheets=external_stylesheets)

app.layout = html.Div([
    # Header Row
    dbc.Row(
        [
            dbc.Col(
                html.H1("Chinese Word Dictionary", className="text-center text-primary"),
                width={"size": 8, "offset": 2},  # Center the title
            )
        ],
        className="mb-4",  # Margin bottom for spacing
    ),
    dbc.Row(
        [
            dbc.Col(
                html.Div("My Personal Chinese Word Repository.", 
                         className="text-center text-muted", 
                         style={"font-size": "1.25rem"}),  # Smaller subtitle
                width={"size": 8, "offset": 2},  # Center the subtitle
            )
        ],
        className="mb-5",  # Margin bottom for spacing
    ),
    html.Div([
        html.Div(
            dcc.Link(f"{page['name']} - {page['path']}", href=page["relative_path"])
        ) for page in dash.page_registry.values()
    ]),
    html.Hr(),
    html.Div(id='page-content'),
        html.Div(
        dash.page_container,
        style={
            "padding": "20px",  # Add padding around the page content
            "background-color": "#f8f9fa",  # Light background color
            "border-radius": "10px",  # Rounded corners for the page container
            "box-shadow": "0 4px 8px rgba(0, 0, 0, 0.1)",  # Subtle shadow for a card-like effect
            "margin-top": "20px"  # Space above the content
        }
    )
])

if __name__ == '__main__':
    app.run(debug=True)