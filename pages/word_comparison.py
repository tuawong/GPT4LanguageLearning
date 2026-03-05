# Import packages
import dash
from dash import html, dash_table, dcc, callback, Output, Input, State, ctx
import pandas as pd
import dash_bootstrap_components as dbc

from main.translation import WordComparisonPipeline
from main.sql import load_word_comparisons, sql_insert_word_comparison
from database import init_db

# Ensure the WordComparison table exists
init_db()

dash.register_page(__name__, path='/word-comparison', name='Word Comparison')

comparison_pipe = WordComparisonPipeline()

# Columns the LLM may return without spaces (Word1 vs Word 1)
COL_RENAME = {
    'Word1': 'Word 1',
    'Word1 Pinyin': 'Word 1 Pinyin',
    'Word2': 'Word 2',
    'Word2 Pinyin': 'Word 2 Pinyin',
}

DISPLAY_COLS = [
    'Word 1', 'Word 1 Pinyin',
    'Word 2', 'Word 2 Pinyin',
    'Meaning',
    'Part of Speech 1', 'Part of Speech 2',
    'Word 1 Nuance', 'Word 2 Nuance',
    'Word 1 Tone', 'Word 2 Tone',
    'Word 1 Example', 'Word 1 Example Pinyin', 'Word 1 Example Meaning',
    'Word 2 Example', 'Word 2 Example Pinyin', 'Word 2 Example Meaning',
]

SAVED_DISPLAY_COLS = DISPLAY_COLS + ['Added Date']

_table_style = dict(
    sort_action='native',
    style_table={'overflowX': 'auto', 'width': '100%'},
    style_cell={
        'textAlign': 'left',
        'padding': '10px',
        'fontFamily': 'Arial',
        'whiteSpace': 'normal',
        'height': 'auto',
        'minWidth': '100px',
        'maxWidth': '280px',
    },
    style_header={
        'backgroundColor': '#f8f9fa',
        'fontWeight': 'bold',
    },
    style_data={
        'backgroundColor': '#ffffff',
        'color': '#212529',
    },
)


def _blank_cols(col_list):
    return [{'name': c, 'id': c} for c in col_list]


# ── Layout ──────────────────────────────────────────────────────────────────
layout = dbc.Container([

    dbc.Row([
        dbc.Col(html.H4("Word Comparison", className="mb-4"), width=12)
    ]),

    # ── Input section ───────────────────────────────────────────────────────
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.B("Word 1"),
                    dbc.Input(
                        id='wc-word1',
                        type='text',
                        placeholder='e.g. 看',
                        debounce=False,
                        style={'width': '100%', 'marginTop': '6px'}
                    ),
                ])
            ], className="mb-3 shadow-sm")
        ], width=3),

        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.B("Word 2"),
                    dbc.Input(
                        id='wc-word2',
                        type='text',
                        placeholder='e.g. 瞧',
                        debounce=False,
                        style={'width': '100%', 'marginTop': '6px'}
                    ),
                ])
            ], className="mb-3 shadow-sm")
        ], width=3),

        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.B("Actions"),
                    dbc.ButtonGroup([
                        dbc.Button('Compare', id='wc-compare-button', n_clicks=0, color='primary',
                                   style={'marginTop': '6px'}),
                        dbc.Button('Save to DB', id='wc-save-button', n_clicks=0, color='success',
                                   style={'marginTop': '6px', 'marginLeft': '8px'}),
                    ], style={'display': 'flex', 'marginTop': '6px'}),
                ])
            ], className="mb-3 shadow-sm")
        ], width=3),
    ]),

    # Compare status
    dbc.Row([
        dbc.Col(
            html.Div(id='wc-compare-status', style={'color': '#6c757d', 'marginBottom': '8px'}),
            width=12
        )
    ]),

    # Store holding the current LLM result as JSON
    dcc.Store(id='wc-result-store'),

    html.Hr(),

    # ── Current comparison result ────────────────────────────────────────────
    dbc.Row([
        dbc.Col(html.H5("Comparison Result", className="mb-3 text-secondary"), width=12)
    ]),

    dcc.Loading(
        type='default',
        children=[
            dbc.Row(dbc.Col(
                dash_table.DataTable(
                    id='wc-result-table',
                    data=[],
                    columns=_blank_cols(DISPLAY_COLS),
                    page_size=5,
                    **_table_style,
                ),
                width=12,
                className="shadow-lg p-3 mb-5 bg-white rounded"
            )),
        ]
    ),

    html.Hr(),

    # ── Saved comparisons section ────────────────────────────────────────────
    dbc.Row([
        dbc.Col(html.H5("All Saved Comparisons", className="mb-3 text-secondary"), width=12)
    ]),

    # Save status (shown after saving)
    dbc.Row([
        dbc.Col(
            html.Div(id='wc-save-status', style={'color': '#6c757d', 'marginBottom': '8px'}),
            width=12
        )
    ]),

    dbc.Row(dbc.Col(
        dash_table.DataTable(
            id='wc-saved-table',
            data=[],
            columns=_blank_cols(SAVED_DISPLAY_COLS),
            page_size=15,
            **_table_style,
        ),
        width=12,
        className="shadow-lg p-3 mb-4 bg-white rounded"
    )),

    dbc.Row([
        dbc.Col(
            dbc.Button('Reload Saved', id='wc-reload-button', n_clicks=0, color='secondary'),
            width='auto'
        )
    ], className="mb-5"),

], fluid=True)


# ── Callbacks ────────────────────────────────────────────────────────────────

@callback(
    Output('wc-result-store', 'data'),
    Output('wc-result-table', 'data'),
    Output('wc-result-table', 'columns'),
    Output('wc-compare-status', 'children'),
    Input('wc-compare-button', 'n_clicks'),
    State('wc-word1', 'value'),
    State('wc-word2', 'value'),
    prevent_initial_call=True,
)
def run_comparison(n_clicks, word1, word2):
    """Call LLM, parse result, show it — but do not save to DB yet."""
    if not word1 or not word2:
        return None, [], _blank_cols(DISPLAY_COLS), "Please enter both words before comparing."

    word1, word2 = word1.strip(), word2.strip()

    try:
        result_df = comparison_pipe.run(word1, word2)
    except Exception as e:
        return None, [], _blank_cols(DISPLAY_COLS), f"Error during comparison: {e}"

    result_df = result_df.rename(columns=COL_RENAME)
    cols_present = [c for c in DISPLAY_COLS if c in result_df.columns]

    return (
        result_df.to_json(orient='records'),
        result_df[cols_present].to_dict('records'),
        _blank_cols(cols_present),
        f"Comparison for '{word1}' vs '{word2}' generated. Click 'Save to DB' to persist it.",
    )


@callback(
    Output('wc-saved-table', 'data'),
    Output('wc-saved-table', 'columns'),
    Output('wc-save-status', 'children'),
    Input('wc-save-button', 'n_clicks'),
    Input('wc-reload-button', 'n_clicks'),
    State('wc-result-store', 'data'),
    prevent_initial_call=True,
)
def save_or_reload(save_clicks, reload_clicks, stored_json):
    """Save the current result to DB (Save button), or reload the saved table (Reload button)."""
    triggered = ctx.triggered_id

    if triggered == 'wc-save-button':
        if not stored_json:
            return [], _blank_cols(SAVED_DISPLAY_COLS), "Nothing to save — run a comparison first."

        result_df = pd.read_json(stored_json, orient='records')
        result_df = result_df.rename(columns=COL_RENAME)
        message = sql_insert_word_comparison(result_df)
        saved_df = load_word_comparisons()
        cols_present = [c for c in SAVED_DISPLAY_COLS if c in saved_df.columns]
        return (
            saved_df[cols_present].to_dict('records') if not saved_df.empty else [],
            _blank_cols(cols_present),
            message,
        )

    # Reload button
    saved_df = load_word_comparisons()
    if saved_df.empty:
        return [], _blank_cols(SAVED_DISPLAY_COLS), "No comparisons saved yet."
    cols_present = [c for c in SAVED_DISPLAY_COLS if c in saved_df.columns]
    return (
        saved_df[cols_present].to_dict('records'),
        _blank_cols(cols_present),
        f"Loaded {len(saved_df)} saved comparisons.",
    )
