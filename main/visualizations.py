import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def prepare_df(df: pd.DataFrame) -> pd.DataFrame:
    """Prepare dataframe with calculated columns."""
    df = df.copy()
    df['Num Pinyin Wrong'] = df['Quiz Attempts'] - df['Num Pinyin Correct']
    df['Num Meaning Wrong'] = df['Quiz Attempts'] - df['Num Meaning Correct']
    df['Last Quiz'] = pd.to_datetime(df['Last Quiz'], format='mixed', errors='coerce')
    df['Added Date'] = pd.to_datetime(df['Added Date'], format='mixed', errors='coerce')
    return df


def create_quiz_by_date_chart(df: pd.DataFrame) -> go.Figure:
    """1) Total quiz attempts by day - line graph with correct/wrong breakdown."""
    quiz_by_date = df.groupby('Last Quiz').agg({
        'Quiz Attempts': 'sum',
        'Num Pinyin Correct': 'sum',
        'Num Meaning Correct': 'sum',
        'Num Pinyin Wrong': 'sum',
        'Num Meaning Wrong': 'sum'
    }).reset_index()

    quiz_by_date['Total Correct'] = quiz_by_date['Num Pinyin Correct'] + quiz_by_date['Num Meaning Correct']
    quiz_by_date['Total Wrong'] = quiz_by_date['Num Pinyin Wrong'] + quiz_by_date['Num Meaning Wrong']

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=quiz_by_date['Last Quiz'],
        y=quiz_by_date['Total Correct'],
        mode='lines+markers',
        name='Correct',
        line=dict(color='green')
    ))
    fig.add_trace(go.Scatter(
        x=quiz_by_date['Last Quiz'],
        y=quiz_by_date['Total Wrong'],
        mode='lines+markers',
        name='Wrong',
        line=dict(color='red')
    ))
    fig.update_layout(
        title='Quiz Attempts by Day (Correct vs Wrong)',
        xaxis_title='Date',
        yaxis_title='Number of Attempts',
        hovermode='x unified'
    )
    return fig


def create_category_performance_chart(df: pd.DataFrame) -> go.Figure:
    """2) Count of words by category with right/wrong percentage (stacked bar)."""
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
        marker_color='green',
        text=category_stats['Correct %'].round(1).astype(str) + '%',
        textposition='inside'
    ))
    fig.add_trace(go.Bar(
        x=category_stats['Word Category'],
        y=category_stats['Wrong %'],
        name='Wrong %',
        marker_color='red',
        text=category_stats['Wrong %'].round(1).astype(str) + '%',
        textposition='inside'
    ))
    fig.update_layout(
        title='Quiz Performance by Word Category',
        xaxis_title='Category',
        yaxis_title='Percentage',
        barmode='stack',
        xaxis_tickangle=-45
    )
    return fig


def create_top_errors_chart(df: pd.DataFrame) -> go.Figure:
    """3) Top 10 words with pinyin wrong / meaning wrong (ranked by % incorrect, then by count)."""
    # Top 10 Pinyin Wrong
    top_pinyin = df.groupby('Word').agg({
        'Num Pinyin Wrong': 'sum',
        'Quiz Attempts': 'sum'
    }).reset_index()
    top_pinyin = top_pinyin[top_pinyin['Quiz Attempts'] > 1]
    top_pinyin['Pinyin Wrong %'] = (top_pinyin['Num Pinyin Wrong'] / top_pinyin['Quiz Attempts'] * 100).round(1)
    top_pinyin = top_pinyin[top_pinyin['Num Pinyin Wrong'] >= 1].sort_values(
        by=['Pinyin Wrong %', 'Num Pinyin Wrong'], ascending=[False, False]
    ).head(10)
    top_pinyin['Label'] = '(' + top_pinyin['Pinyin Wrong %'].astype(str) + '%, ' + top_pinyin['Quiz Attempts'].astype(str) + ')'

    # Top 10 Meaning Wrong
    top_meaning = df.groupby('Word').agg({
        'Num Meaning Wrong': 'sum',
        'Quiz Attempts': 'sum'
    }).reset_index()
    top_meaning = top_meaning[top_meaning['Quiz Attempts'] > 1]
    top_meaning['Meaning Wrong %'] = (top_meaning['Num Meaning Wrong'] / top_meaning['Quiz Attempts'] * 100).round(1)
    top_meaning = top_meaning[top_meaning['Num Meaning Wrong'] >= 1].sort_values(
        by=['Meaning Wrong %', 'Num Meaning Wrong'], ascending=[False, False]
    ).head(10)
    top_meaning['Label'] = '(' + top_meaning['Meaning Wrong %'].astype(str) + '%, ' + top_meaning['Quiz Attempts'].astype(str) + ')'

    fig = make_subplots(rows=1, cols=2, subplot_titles=('Top 10 Pinyin Wrong', 'Top 10 Meaning Wrong'))

    fig.add_trace(go.Bar(
        y=top_pinyin['Word'],
        x=top_pinyin['Pinyin Wrong %'],
        orientation='h',
        marker_color='coral',
        text=top_pinyin['Label'],
        textposition='outside'
    ), row=1, col=1)

    fig.add_trace(go.Bar(
        y=top_meaning['Word'],
        x=top_meaning['Meaning Wrong %'],
        orientation='h',
        marker_color='steelblue',
        text=top_meaning['Label'],
        textposition='outside'
    ), row=1, col=2)

    fig.update_layout(
        title='Top 10 Words with Highest Error Rate',
        showlegend=False,
        height=500,
        margin=dict(r=100)
    )
    fig.update_xaxes(title_text='% Incorrect', row=1, col=1, range=[0, 120])
    fig.update_xaxes(title_text='% Incorrect', row=1, col=2, range=[0, 120])
    fig.update_yaxes(autorange='reversed')
    return fig


def create_words_by_category_chart(df: pd.DataFrame) -> go.Figure:
    """4) Count of Words by Category."""
    words_by_category = df.groupby('Word Category')['Word'].count().reset_index()
    words_by_category.columns = ['Word Category', 'Count']
    words_by_category = words_by_category.sort_values('Count', ascending=True)

    fig = go.Figure(go.Bar(
        x=words_by_category['Count'],
        y=words_by_category['Word Category'],
        orientation='h',
        marker_color='teal',
        text=words_by_category['Count'],
        textposition='outside'
    ))
    fig.update_layout(
        title='Word Count by Category',
        xaxis_title='Number of Words',
        yaxis_title='Category',
        height=600
    )
    return fig


def create_vocabulary_growth_chart(df: pd.DataFrame) -> go.Figure:
    """7) Words Added Over Time (cumulative)."""
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
        line=dict(color='royalblue')
    ))
    fig.update_layout(
        title='Vocabulary Growth Over Time',
        xaxis_title='Date',
        yaxis_title='Total Words in Dictionary'
    )
    return fig


def create_quiz_coverage_chart(df: pd.DataFrame) -> go.Figure:
    """8) Quiz Coverage - Words Quizzed vs Not Quizzed."""
    quizzed = (df['Quiz Attempts'] > 0).sum()
    not_quizzed = (df['Quiz Attempts'] == 0).sum()

    fig = go.Figure(go.Pie(
        labels=['Quizzed', 'Not Quizzed'],
        values=[quizzed, not_quizzed],
        marker_colors=['green', 'lightgray'],
        textinfo='label+percent+value',
        hole=0.4
    ))
    fig.update_layout(title='Quiz Coverage')
    return fig