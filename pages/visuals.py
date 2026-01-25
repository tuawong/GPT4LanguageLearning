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

layout = dbc.Container([
    # Page Title and Reload Button
    dbc.Row([
        dbc.Col([
            html.H2('Quiz Statistics Dashboard', className='text-center mb-4')
        ], width=10),
        dbc.Col([
            dbc.Button('Reload Data', id='stats-reload-button', n_clicks=0, color='primary', className='mt-2')
        ], width=2, className='text-end'),
    ]),
    
    # Section 1: Overview Stats
    html.H4('📊 Overview', className='text-muted mb-3'),
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dcc.Graph(id='vocabulary-growth', figure=create_vocabulary_growth_chart(orig_df))
                ])
            ])
        ], width=8),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dcc.Graph(id='quiz-coverage', figure=create_quiz_coverage_chart(orig_df))
                ])
            ])
        ], width=4),
    ], className='mb-4'),
    
    # Section 2: Word Distribution
    html.H4('📚 Word Distribution', className='text-muted mb-3'),
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dcc.Graph(id='words-by-category', figure=create_words_by_category_chart(orig_df))
                ])
            ])
        ], width=6),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dcc.Graph(id='category-performance', figure=create_category_performance_chart(orig_df))
                ])
            ])
        ], width=6),
    ], className='mb-4'),
    
    # Section 3: Quiz Performance
    html.H4('📈 Quiz Performance', className='text-muted mb-3'),
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dcc.Graph(id='quiz-by-date', figure=create_quiz_by_date_chart(orig_df))
                ])
            ])
        ], width=12),
    ], className='mb-4'),
    
    # Section 4: Problem Areas
    html.H4('⚠️ Areas to Improve', className='text-muted mb-3'),
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dcc.Graph(id='top-errors', figure=create_top_errors_chart(orig_df))
                ])
            ])
        ], width=12),
    ], className='mb-4'),
    
], fluid=True)


@callback(
    [Output('vocabulary-growth', 'figure'),
     Output('quiz-coverage', 'figure'),
     Output('words-by-category', 'figure'),
     Output('category-performance', 'figure'),
     Output('quiz-by-date', 'figure'),
     Output('top-errors', 'figure')],
    Input('stats-reload-button', 'n_clicks'),
    prevent_initial_call=True
)
def update_charts(n_clicks):
    """Update all charts when reload button is clicked."""
    df = load_dict()
    df = prepare_df(df)
    
    return (
        create_vocabulary_growth_chart(df),
        create_quiz_coverage_chart(df),
        create_words_by_category_chart(df),
        create_category_performance_chart(df),
        create_quiz_by_date_chart(df),
        create_top_errors_chart(df)
    )