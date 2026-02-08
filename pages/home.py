import dash
from dash import html, dcc
import dash_bootstrap_components as dbc

dash.register_page(__name__, path='/', name='Home')

# Feature cards data
features = [
    {
        "title": "词典 Dictionary",
        "description": "Browse and manage your personal Chinese word repository. Filter by date, category, and rarity.",
        "icon": "fa-book",
        "href": "/dictionary",
        "color": "primary"
    },
    {
        "title": "词组 Phrases",
        "description": "Explore Chinese phrases and expressions to enhance your vocabulary.",
        "icon": "fa-comments",
        "href": "/phrases",
        "color": "success"
    },
    {
        "title": "单词测验 Word Quiz",
        "description": "Test your knowledge of Chinese words with interactive quizzes.",
        "icon": "fa-spell-check",
        "href": "/wordquiz",
        "color": "info"
    },
    {
        "title": "词组测验 Phrase Quiz",
        "description": "Challenge yourself with phrase-based quizzes to reinforce learning.",
        "icon": "fa-clipboard-question",
        "href": "/phrasequiz",
        "color": "warning"
    },
    {
        "title": "词组生成 Phrase Generator",
        "description": "Generate new phrases using AI to expand your learning materials.",
        "icon": "fa-wand-magic-sparkles",
        "href": "/phrasegen",
        "color": "danger"
    },
    {
        "title": "翻译 Translation",
        "description": "Translate text between Chinese and English with AI assistance.",
        "icon": "fa-language",
        "href": "/translation",
        "color": "secondary"
    },
    {
        "title": "统计 Quiz Statistics",
        "description": "Track your progress and visualize your learning journey over time.",
        "icon": "fa-chart-line",
        "href": "/stats",
        "color": "dark"
    },
]

def create_feature_card(feature):
    return dbc.Col([
        dbc.Card([
            dbc.CardBody([
                html.Div([
                    html.I(className=f"fas {feature['icon']} fa-3x text-{feature['color']} mb-3"),
                ], className="text-center"),
                html.H4(feature["title"], className="card-title text-center"),
                html.P(feature["description"], className="card-text text-muted text-center"),
                dbc.Button(
                    "Explore",
                    href=feature["href"],
                    color=feature["color"],
                    outline=True,
                    className="w-100 mt-2"
                ),
            ])
        ], className="h-100 shadow-sm hover-shadow", style={"transition": "transform 0.2s", "cursor": "pointer"})
    ], md=4, sm=6, xs=12, className="mb-4")

# Hero section
hero_section = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.Div([
                html.H1([
                    html.Span("学", className="text-danger", style={"font-size": "4rem"}),
                    html.Span("中", className="text-warning", style={"font-size": "4rem"}),
                    html.Span("文", className="text-success", style={"font-size": "4rem"}),
                ], className="text-center mb-3"),
                html.H2("Master Chinese, One Word at a Time", className="text-center text-primary mb-4"),
                html.P(
                    "Your personal Chinese learning companion. Build vocabulary, practice with quizzes, "
                    "and track your progress as you journey through the Chinese language.",
                    className="text-center text-muted lead mb-4",
                    style={"max-width": "700px", "margin": "0 auto"}
                ),
                html.Div([
                    dbc.Button("Start Learning", href="/dictionary", color="primary", size="lg", className="me-3"),
                    dbc.Button("Take a Quiz", href="/wordquiz", color="outline-primary", size="lg"),
                ], className="text-center mb-5"),
            ], className="py-5")
        ], width=12)
    ])
], fluid=True, className="bg-light rounded-3 py-4 mb-5")

# Stats section (placeholder - can be dynamic later)
stats_section = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.Div([
                html.I(className="fas fa-book-open fa-2x text-primary mb-2"),
                html.H3("词汇", className="text-primary"),
                html.P("Words", className="text-muted"),
            ], className="text-center")
        ], md=3, sm=6, className="mb-3"),
        dbc.Col([
            html.Div([
                html.I(className="fas fa-quote-left fa-2x text-success mb-2"),
                html.H3("短语", className="text-success"),
                html.P("Phrases", className="text-muted"),
            ], className="text-center")
        ], md=3, sm=6, className="mb-3"),
        dbc.Col([
            html.Div([
                html.I(className="fas fa-brain fa-2x text-warning mb-2"),
                html.H3("测验", className="text-warning"),
                html.P("Quizzes", className="text-muted"),
            ], className="text-center")
        ], md=3, sm=6, className="mb-3"),
        dbc.Col([
            html.Div([
                html.I(className="fas fa-robot fa-2x text-info mb-2"),
                html.H3("AI 助手", className="text-info"),
                html.P("AI Powered", className="text-muted"),
            ], className="text-center")
        ], md=3, sm=6, className="mb-3"),
    ], className="py-4")
], fluid=True, className="mb-5")

# Features section
features_section = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H2("Features", className="text-center mb-2"),
            html.P("Everything you need to master Chinese", className="text-center text-muted mb-4"),
            html.Hr(className="mb-4"),
        ], width=12)
    ]),
    dbc.Row([
        create_feature_card(feature) for feature in features
    ], className="justify-content-center")
], fluid=True)

# Footer
footer_section = html.Div([
    html.Hr(className="mt-5"),
    html.P(
        "Built with ❤️ for Chinese language learners",
        className="text-center text-muted py-3"
    )
])

# Main layout
layout = dbc.Container([
    hero_section,
    stats_section,
    features_section,
    footer_section,
], fluid=True, className="px-4")