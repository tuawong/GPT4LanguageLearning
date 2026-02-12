import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Common layout settings for all charts
CHART_TEMPLATE = "plotly_white"
CHART_FONT = dict(family="Arial, sans-serif", size=12)
CHART_MARGIN = dict(l=40, r=40, t=40, b=40)
COLORS = {
    'primary': '#0d6efd',
    'success': '#198754',
    'danger': '#dc3545',
    'warning': '#ffc107',
    'info': '#0dcaf0',
    'teal': '#20c997',
    'coral': '#ff6b6b',
    'steelblue': '#4682b4'
}


def prepare_df(df: pd.DataFrame) -> pd.DataFrame:
    """Prepare dataframe with calculated columns."""
    df = df.copy()
    df['Num Pinyin Wrong'] = df['Quiz Attempts'] - df['Num Pinyin Correct']
    df['Num Meaning Wrong'] = df['Quiz Attempts'] - df['Num Meaning Correct']
    df['Last Quiz'] = pd.to_datetime(df['Last Quiz'], format='mixed', errors='coerce')
    df['Added Date'] = pd.to_datetime(df['Added Date'], format='mixed', errors='coerce')
    return df


def create_quiz_by_date_chart(df: pd.DataFrame) -> go.Figure:
    """Quiz attempts by day with total attempts and percentage correct."""
    quiz_by_date = df.groupby('Last Quiz').agg({
        'Quiz Attempts': 'sum',
        'Num Pinyin Correct': 'sum',
        'Num Meaning Correct': 'sum'
    }).reset_index()

    quiz_by_date['Total Correct'] = quiz_by_date['Num Pinyin Correct'] + quiz_by_date['Num Meaning Correct']
    quiz_by_date['Total Attempts'] = quiz_by_date['Quiz Attempts'] * 2  # Each quiz has pinyin and meaning
    quiz_by_date['Correct %'] = (quiz_by_date['Total Correct'] / quiz_by_date['Total Attempts'] * 100).round(1)

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(
        x=quiz_by_date['Last Quiz'],
        y=quiz_by_date['Total Attempts'],
        mode='lines+markers',
        name='Total Attempts',
        line=dict(color=COLORS['primary'], width=2),
        marker=dict(size=6),
        fill='tozeroy',
        fillcolor='rgba(13, 110, 253, 0.1)'
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=quiz_by_date['Last Quiz'],
        y=quiz_by_date['Correct %'],
        mode='lines+markers',
        name='Correct %',
        line=dict(color=COLORS['success'], width=2),
        marker=dict(size=6)
    ), secondary_y=True)
    fig.update_layout(
        template=CHART_TEMPLATE,
        font=CHART_FONT,
        margin=CHART_MARGIN,
        xaxis_title='Date',
        hovermode='x unified',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        height=350
    )
    fig.update_yaxes(title_text='Total Attempts', secondary_y=False)
    fig.update_yaxes(title_text='Correct %', secondary_y=True, range=[0, 100])
    return fig


def create_category_performance_chart(df: pd.DataFrame) -> go.Figure:
    """Quiz performance by word category (stacked bar)."""
    category_stats = df.groupby('Word Category').agg({
        'Word': 'count',
        'Num Pinyin Correct': 'sum',
        'Num Meaning Correct': 'sum',
        'Num Pinyin Wrong': 'sum',
        'Num Meaning Wrong': 'sum'
    }).reset_index()

    category_stats['Total Correct'] = category_stats['Num Pinyin Correct'] + category_stats['Num Meaning Correct']
    category_stats['Total Wrong'] = category_stats['Num Pinyin Wrong'] + category_stats['Num Meaning Wrong']
    category_stats['Total Attempts'] = category_stats['Total Correct'] + category_stats['Total Wrong']
    category_stats['Correct %'] = (category_stats['Total Correct'] / category_stats['Total Attempts'] * 100).fillna(0)
    category_stats['Wrong %'] = (category_stats['Total Wrong'] / category_stats['Total Attempts'] * 100).fillna(0)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=category_stats['Word Category'],
        y=category_stats['Correct %'],
        name='Correct %',
        marker_color=COLORS['success'],
        text=category_stats['Correct %'].round(1).astype(str) + '%',
        textposition='inside',
        textfont=dict(color='white')
    ))
    fig.add_trace(go.Bar(
        x=category_stats['Word Category'],
        y=category_stats['Wrong %'],
        name='Wrong %',
        marker_color=COLORS['danger'],
        text=category_stats['Wrong %'].round(1).astype(str) + '%',
        textposition='inside',
        textfont=dict(color='white')
    ))
    fig.update_layout(
        template=CHART_TEMPLATE,
        font=CHART_FONT,
        margin=CHART_MARGIN,
        xaxis_title='Category',
        yaxis_title='Percentage',
        barmode='stack',
        xaxis_tickangle=-45,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        height=400
    )
    return fig

# ...existing code...

def create_top_errors_chart(df: pd.DataFrame) -> go.Figure:
    """Top 10 words with pinyin/meaning errors."""
    # Top 10 Pinyin Wrong
    top_pinyin = df.groupby('Word').agg({
        'Num Pinyin Wrong': 'sum',
        'Quiz Attempts': 'sum',
        'Pinyin': 'first'
    }).reset_index()
    top_pinyin = top_pinyin[top_pinyin['Quiz Attempts'] > 1]
    top_pinyin['Pinyin Wrong %'] = (top_pinyin['Num Pinyin Wrong'] / top_pinyin['Quiz Attempts'] * 100).round(1)
    top_pinyin = top_pinyin[top_pinyin['Num Pinyin Wrong'] >= 1].sort_values(
        by=['Pinyin Wrong %', 'Num Pinyin Wrong'], ascending=[False, False]
    ).head(10)
    top_pinyin['Label'] = '(' + top_pinyin['Pinyin Wrong %'].astype(str) + '%, ' + top_pinyin['Quiz Attempts'].astype(str) + ')'
    top_pinyin['Word Display'] = top_pinyin['Word'] + ' (' + top_pinyin['Pinyin'] + ')'

    # Top 10 Meaning Wrong
    top_meaning = df.groupby('Word').agg({
        'Num Meaning Wrong': 'sum',
        'Quiz Attempts': 'sum',
        'Pinyin': 'first'
    }).reset_index()
    top_meaning = top_meaning[top_meaning['Quiz Attempts'] > 1]
    top_meaning['Meaning Wrong %'] = (top_meaning['Num Meaning Wrong'] / top_meaning['Quiz Attempts'] * 100).round(1)
    top_meaning = top_meaning[top_meaning['Num Meaning Wrong'] >= 1].sort_values(
        by=['Meaning Wrong %', 'Num Meaning Wrong'], ascending=[False, False]
    ).head(10)
    top_meaning['Label'] = '(' + top_meaning['Meaning Wrong %'].astype(str) + '%, ' + top_meaning['Quiz Attempts'].astype(str) + ')'
    top_meaning['Word Display'] = top_meaning['Word'] + ' (' + top_meaning['Pinyin'] + ')'

    fig = make_subplots(
        rows=1, cols=2, 
        subplot_titles=('Top 10 Pinyin Errors', 'Top 10 Meaning Errors'),
        horizontal_spacing=0.2
    )

    fig.add_trace(go.Bar(
        y=top_pinyin['Word Display'],
        x=top_pinyin['Pinyin Wrong %'],
        orientation='h',
        marker_color=COLORS['coral'],
        text=top_pinyin['Label'],
        textposition='outside',
        textfont=dict(size=10)
    ), row=1, col=1)

    fig.add_trace(go.Bar(
        y=top_meaning['Word Display'],
        x=top_meaning['Meaning Wrong %'],
        orientation='h',
        marker_color=COLORS['steelblue'],
        text=top_meaning['Label'],
        textposition='outside',
        textfont=dict(size=10)
    ), row=1, col=2)

    fig.update_layout(
        template=CHART_TEMPLATE,
        font=CHART_FONT,
        showlegend=False,
        height=400,
        margin=dict(l=80, r=80, t=60, b=40)
    )
    fig.update_xaxes(title_text='% Incorrect', row=1, col=1, range=[0, 120])
    fig.update_xaxes(title_text='% Incorrect', row=1, col=2, range=[0, 120])
    fig.update_yaxes(autorange='reversed', tickfont=dict(size=20), row=1, col=1)
    fig.update_yaxes(autorange='reversed', tickfont=dict(size=20), row=1, col=2)
    return fig


def create_words_by_category_chart(df: pd.DataFrame) -> go.Figure:
    """Count of words by category."""
    words_by_category = df.groupby('Word Category')['Word'].count().reset_index()
    words_by_category.columns = ['Word Category', 'Count']
    words_by_category = words_by_category.sort_values('Count', ascending=True)
    
    #Filter categories with at least 5 words
    words_by_category = words_by_category[words_by_category['Count'] >= 10]

    fig = go.Figure(go.Bar(
        x=words_by_category['Count'],
        y=words_by_category['Word Category'],
        orientation='h',
        marker_color=COLORS['teal'],
        text=words_by_category['Count'],
        textposition='outside',
        textfont=dict(size=11)
    ))
    fig.update_layout(
        template=CHART_TEMPLATE,
        font=CHART_FONT,
        margin=CHART_MARGIN,
        xaxis_title='Number of Words',
        yaxis_title='',
        height=760
    )
    return fig


def create_vocabulary_growth_chart(df: pd.DataFrame) -> go.Figure:
    """Cumulative vocabulary growth over time."""
    words_over_time = df.groupby(df['Added Date'].dt.date)['Word'].count().reset_index()
    words_over_time.columns = ['Date', 'Words Added']
    words_over_time['Cumulative'] = words_over_time['Words Added'].cumsum()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=words_over_time['Date'],
        y=words_over_time['Cumulative'],
        mode='lines+markers',
        name='Total Words',
        fill='tozeroy',
        line=dict(color=COLORS['primary'], width=2),
        marker=dict(size=6),
        fillcolor='rgba(13, 110, 253, 0.1)'
    ))
    fig.update_layout(
        template=CHART_TEMPLATE,
        font=CHART_FONT,
        margin=CHART_MARGIN,
        xaxis_title='Date',
        yaxis_title='Total Words',
        height=350
    )
    return fig


def create_quiz_coverage_chart(df: pd.DataFrame) -> go.Figure:
    """Words quizzed vs not quizzed by rarity (donut chart with 4 categories)."""
    common_df = df[df['Word Rarity'] == 'Common']
    rare_df = df[df['Word Rarity'] == 'Rare']

    common_quizzed = (common_df['Quiz Attempts'] > 0).sum()
    common_not_quizzed = (common_df['Quiz Attempts'] == 0).sum()
    rare_quizzed = (rare_df['Quiz Attempts'] > 0).sum()
    rare_not_quizzed = (rare_df['Quiz Attempts'] == 0).sum()

    total_quizzed = common_quizzed + rare_quizzed

    fig = go.Figure(go.Pie(
        labels=['Common - Quizzed', 'Common - Not Quizzed', 'Rare - Quizzed', 'Rare - Not Quizzed'],
        values=[common_quizzed, common_not_quizzed, rare_quizzed, rare_not_quizzed],
        marker_colors=[COLORS['success'], '#a3cfbb', COLORS['steelblue'], '#a8c8e0'],
        textinfo='label+percent',
        textfont=dict(size=11),
        hole=0.5,
        hovertemplate='%{label}: %{value} words<extra></extra>'
    ))
    fig.update_layout(
        template=CHART_TEMPLATE,
        font=CHART_FONT,
        margin=dict(l=20, r=20, t=20, b=20),
        showlegend=False,
        height=400,
        annotations=[dict(
            text=f'{total_quizzed}<br>quizzed',
            x=0.5, y=0.5,
            font_size=16,
            showarrow=False
        )]
    )
    return fig