import dash
from dash import Dash, html, dcc
import dash_bootstrap_components as dbc
from database import init_db, ensure_views_from_files

# Initialize DB and ensure views are created
init_db()
ensure_views_from_files()

external_stylesheets = [dbc.themes.MATERIA]
app = Dash(__name__, use_pages=True, external_stylesheets=external_stylesheets, suppress_callback_exceptions=True)

def sidebar():
    return html.Div(
        dbc.Nav(
            [
                dbc.NavLink(
                    html.Div(page["name"], className="ms-2"),
                    href=page["path"],
                    active="exact",
                )
                for page in dash.page_registry.values()
            ],
            vertical=True,
            pills=True,
            className="bg-light",
        )
    )

def top_navbar():
    return dbc.Navbar(
        dbc.Container(
            [
                #dbc.NavbarBrand("Chinese Word Dictionary", href="/", className="fw-bold text-primary"),               
                # Navigation links aligned to the right
                dbc.Nav(
                    [
                        dbc.NavLink(page["name"], href=page["path"], active="exact")
                        for page in dash.page_registry.values()
                    ],
                    pills=True,
                    className="ms-auto",  # Right align using margin-left: auto
                ),
            ],
            fluid=True,
        ),
        color="dark",
        dark=True,     
        className="mb-4",  # Add some margin below the navbar
    )


app.layout = html.Div([
    top_navbar(),
    # Header Row
    dbc.Row(
        [
            dbc.Col(
                html.H1("Chinese Word Dictionary", className="text-center text-primary"),
                width={"size": 8, "offset": 2},  # Center the title
            )
        ],
        className="mt-4 mb-1",  # Margin top and bottom for spacing
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
    #html.Div([
    #    html.Div(
    #        dcc.Link(f"{page['name']}", href=page["relative_path"])
    #    ) for page in dash.page_registry.values()
    #]),
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