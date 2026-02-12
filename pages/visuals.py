import dash
from dash import html, dcc, callback, Output, Input
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
from main.visualizations import (
    prepare_df,
    create_quiz_by_date_chart,
    create_category_performance_chart,
    create_top_errors_chart,
    create_words_by_category_chart,
    create_vocabulary_growth_chart,
    create_quiz_coverage_chart
)
from main.sql import load_dict

dash.register_page(__name__, path='/stats', name='Quiz Statistics')

# Load and prepare data initially
orig_df = load_dict()
orig_df = prepare_df(orig_df)

# Calculate summary stats
total_words = len(orig_df)
words_quizzed = (orig_df['Quiz Attempts'] > 0).sum()
total_attempts = orig_df['Quiz Attempts'].sum()
avg_accuracy = ((orig_df['Num Pinyin Correct'].sum() + orig_df['Num Meaning Correct'].sum()) / 
                (2 * total_attempts) * 100) if total_attempts > 0 else 0


def create_stat_card(title, value, icon, color):
    """Create a styled stat card."""
    return dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.I(className=f"fas {icon} fa-2x")
                    ], className=f"text-{color}")
                ], width=3, className="d-flex align-items-center justify-content-center"),
                dbc.Col([
                    html.H6(title, className="text-muted mb-1", style={'fontSize': '0.85rem'}),
                    html.H4(value, className="mb-0 fw-bold")
                ], width=9)
            ])
        ])
    ], className="shadow-sm h-100")


layout = dbc.Container([
    # Header Row
    dbc.Row([
        dbc.Col([
            html.H2([
                html.I(className="fas fa-chart-line me-2"),
                'Quiz Statistics Dashboard'
            ], className='mb-0')
        ], width=9),
        dbc.Col([
            dbc.Button([
                html.I(className="fas fa-sync-alt me-2"),
                'Reload Data'
            ], id='stats-reload-button', n_clicks=0, color='primary', className='mt-2')
        ], width=3, className='text-end'),
    ], className='mb-4 align-items-center'),
    
    html.Hr(className='mb-4'),
    
    # Summary Stat Cards
    dbc.Row([
        dbc.Col([
            html.Div(id='stat-total-words', children=create_stat_card("Total Words", f"{total_words:,}", "fa-book", "primary"))
        ], width=3),
        dbc.Col([
            html.Div(id='stat-words-quizzed', children=create_stat_card("Words Quizzed", f"{words_quizzed:,}", "fa-check-circle", "success"))
        ], width=3),
        dbc.Col([
            html.Div(id='stat-total-attempts', children=create_stat_card("Total Attempts", f"{total_attempts:,}", "fa-clipboard-list", "info"))
        ], width=3),
        dbc.Col([
            html.Div(id='stat-avg-accuracy', children=create_stat_card("Avg Accuracy", f"{avg_accuracy:.1f}%", "fa-bullseye", "warning"))
        ], width=3),
    ], className='mb-4'),
    
    # Section 1: Overview - Vocabulary Growth + Quiz Performance stacked on left, Words by Category on right
    dbc.Row([
        dbc.Col([
            html.H5([
                html.I(className="fas fa-chart-area me-2 text-primary"),
                'Overview'
            ], className='mb-3')
        ])
    ]),
    dbc.Row([
        # Left column: Vocabulary Growth stacked on Quiz Performance Over Time
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.I(className="fas fa-seedling me-2"),
                    "Vocabulary Growth"
                ], className="bg-light fw-bold"),
                dbc.CardBody([
                    dcc.Graph(
                        id='vocabulary-growth', 
                        figure=create_vocabulary_growth_chart(orig_df),
                        config={'displayModeBar': False}
                    )
                ])
            ], className="shadow-sm mb-3"),
            dbc.Card([
                dbc.CardHeader([
                    html.I(className="fas fa-chart-line me-2"),
                    "Daily Quiz Activity"
                ], className="bg-light fw-bold"),
                dbc.CardBody([
                    dcc.Graph(
                        id='quiz-by-date', 
                        figure=create_quiz_by_date_chart(orig_df),
                        config={'displayModeBar': False}
                    )
                ])
            ], className="shadow-sm")
        ], width=6),
        # Right column: Words by Category (taller)
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.I(className="fas fa-tags me-2"),
                    "Words by Category"
                ], className="bg-light fw-bold"),
                dbc.CardBody([
                    dcc.Graph(
                        id='words-by-category', 
                        figure=create_words_by_category_chart(orig_df),
                        config={'displayModeBar': False}
                    )
                ])
            ], className="shadow-sm h-100")
        ], width=6),
    ], className='mb-4'),
    
    # Section 2: Performance by Category (full width)
    dbc.Row([
        dbc.Col([
            html.H5([
                html.I(className="fas fa-layer-group me-2 text-success"),
                'Performance by Category'
            ], className='mb-3')
        ])
    ]),
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.I(className="fas fa-percentage me-2"),
                    "Quiz Performance by Category"
                ], className="bg-light fw-bold"),
                dbc.CardBody([
                    dcc.Graph(
                        id='category-performance', 
                        figure=create_category_performance_chart(orig_df),
                        config={'displayModeBar': False}
                    )
                ])
            ], className="shadow-sm")
        ], width=12),
    ], className='mb-4'),
    
    # Section 3: Areas to Improve - Top Errors (9 cols) + Quiz Coverage (3 cols)
    dbc.Row([
        dbc.Col([
            html.H5([
                html.I(className="fas fa-exclamation-triangle me-2 text-danger"),
                'Areas to Improve'
            ], className='mb-3')
        ])
    ]),
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.I(className="fas fa-times-circle me-2"),
                    "Top Error Words"
                ], className="bg-light fw-bold"),
                dbc.CardBody([
                    dcc.Graph(
                        id='top-errors', 
                        figure=create_top_errors_chart(orig_df),
                        config={'displayModeBar': False}
                    )
                ])
            ], className="shadow-sm h-100")
        ], width=8),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.I(className="fas fa-chart-pie me-2"),
                    "Quiz Coverage"
                ], className="bg-light fw-bold"),
                dbc.CardBody([
                    dcc.Graph(
                        id='quiz-coverage', 
                        figure=create_quiz_coverage_chart(orig_df),
                        config={'displayModeBar': False}
                    )
                ])
            ], className="shadow-sm h-100")
        ], width=4),
    ], className='mb-4'),
    
], fluid=True, className="px-4 py-3")


@callback(
    [Output('vocabulary-growth', 'figure'),
     Output('quiz-coverage', 'figure'),
     Output('words-by-category', 'figure'),
     Output('category-performance', 'figure'),
     Output('quiz-by-date', 'figure'),
     Output('top-errors', 'figure'),
     Output('stat-total-words', 'children'),
     Output('stat-words-quizzed', 'children'),
     Output('stat-total-attempts', 'children'),
     Output('stat-avg-accuracy', 'children')],
    Input('stats-reload-button', 'n_clicks')
)
def update_charts(n_clicks):
    """Update all charts and stats when reload button is clicked."""
    if n_clicks == 0:
        return dash.no_update
    
    df = load_dict()
    df = prepare_df(df)
    
    # Calculate updated summary stats
    total_words = len(df)
    words_quizzed = (df['Quiz Attempts'] > 0).sum()
    total_attempts = df['Quiz Attempts'].sum()
    avg_accuracy = ((df['Num Pinyin Correct'].sum() + df['Num Meaning Correct'].sum()) / 
                    (2 * total_attempts) * 100) if total_attempts > 0 else 0
    
    return (
        create_vocabulary_growth_chart(df),
        create_quiz_coverage_chart(df),
        create_words_by_category_chart(df),
        create_category_performance_chart(df),
        create_quiz_by_date_chart(df),
        create_top_errors_chart(df),
        create_stat_card("Total Words", f"{total_words:,}", "fa-book", "primary"),
        create_stat_card("Words Quizzed", f"{words_quizzed:,}", "fa-check-circle", "success"),
        create_stat_card("Total Attempts", f"{total_attempts:,}", "fa-clipboard-list", "info"),
        create_stat_card("Avg Accuracy", f"{avg_accuracy:.1f}%", "fa-bullseye", "warning")
    )