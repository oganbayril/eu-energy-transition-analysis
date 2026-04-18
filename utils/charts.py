import plotly.graph_objects as go


# ── Colour palette ────────────────────────────────────────────────────────────
COLORS = {
    'nuclear':    '#7A7A7A',
    'fossil':     '#C4733A',
    'renewables': '#4CAF50',
    'wind':       '#4AAFB0',
    'solar':      '#E8A838',
    'dependency': '#E05A5A',
    'neutral':    '#5B8DB8',
}

COUNTRY_COLORS = {
    'Germany': '#E05A5A',
    'France':  '#5B8DB8',
    'Italy':   '#4CAF50',
    'Denmark': '#E8A838',
}


# ── Section 1: YoY Changes ────────────────────────────────────────────────────

def chart_yoy_renewable_growth(df):
    """
    Bar chart of EU-wide year-over-year change in renewable production.

    Expected df columns: year, yoy_change_pct
    """
    df = df.dropna(subset=['yoy_change_pct'])
    colors = [COLORS['renewables'] if v >= 0 else COLORS['fossil'] for v in df['yoy_change_pct']]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df['year'],
        y=df['yoy_change_pct'],
        marker_color=colors,
        name='YoY change',
    ))
    fig.add_hline(y=0, line_color='black', line_width=1)
    fig.update_layout(
        title='EU Renewable Production — Year-over-Year % Change',
        xaxis_title=None,
        yaxis_title='YoY Change (%)',
        plot_bgcolor='white',
        yaxis=dict(gridcolor='#eeeeee'),
        showlegend=False,
    )
    return fig


def chart_yoy_fossil_vs_renewable(df):
    """
    Side-by-side bars comparing YoY % change in fossil use vs renewable
    production at EU level — shows whether the two trends mirror each other.

    Expected df columns: year, fossil_yoy_pct, renewable_yoy_pct
    """
    df = df.dropna(subset=['fossil_yoy_pct', 'renewable_yoy_pct'])

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df['year'], y=df['fossil_yoy_pct'],
        name='Fossil fuels', marker_color=COLORS['fossil'],
    ))
    fig.add_trace(go.Bar(
        x=df['year'], y=df['renewable_yoy_pct'],
        name='Renewables', marker_color=COLORS['renewables'],
    ))
    fig.add_hline(y=0, line_color='black', line_width=1)
    fig.update_layout(
        title='EU Fossil vs Renewable — Year-over-Year % Change',
        xaxis_title=None,
        yaxis_title='YoY Change (%)',
        barmode='group',
        plot_bgcolor='white',
        yaxis=dict(gridcolor='#eeeeee'),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
    )
    return fig


# ── Section 2: Rolling Averages ───────────────────────────────────────────────

def chart_rolling_dependency(df):
    """
    Line chart of EU average dependency rate with a 3-year rolling average
    overlaid on the raw annual values.

    Expected df columns: year, avg_dependency, rolling_avg
    """
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['year'], y=df['avg_dependency'],
        name='Annual average',
        line=dict(color=COLORS['dependency'], width=1, dash='dot'),
        opacity=0.6,
    ))
    fig.add_trace(go.Scatter(
        x=df['year'], y=df['rolling_avg'],
        name='3-year rolling avg',
        line=dict(color=COLORS['dependency'], width=3),
    ))
    fig.update_layout(
        title='EU Average Energy Dependency Rate',
        xaxis_title=None,
        yaxis_title='Dependency Rate (%)',
        plot_bgcolor='white',
        yaxis=dict(gridcolor='#eeeeee'),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
    )
    return fig


def chart_rolling_renewable_share(df, countries):
    """
    Line chart of 3-year rolling average renewable share for a given list
    of countries — used to compare smoothed trajectories.

    Expected df columns: year, country, rolling_share
    countries: list of country names to include
    """
    fig = go.Figure()
    for country in countries:
        c_df = df[df['country'] == country]
        fig.add_trace(go.Scatter(
            x=c_df['year'], y=c_df['rolling_share'],
            name=country,
            line=dict(color=COUNTRY_COLORS.get(country, '#888888'), width=2.5),
        ))
    fig.update_layout(
        title='Renewable Share — 3-Year Rolling Average',
        xaxis_title=None,
        yaxis_title='Renewable Share (%)',
        plot_bgcolor='white',
        yaxis=dict(gridcolor='#eeeeee'),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
    )
    return fig


# ── Section 3: Germany Nuclear Phaseout ──────────────────────────────────────

def chart_germany_indexed(df):
    """
    Line chart with all metrics indexed to 2005 = 100, so nuclear decline
    and renewable growth are on the same scale.

    Expected df columns: year, nuclear_idx, renewable_idx, fossil_idx, dependency_idx
    """
    traces = [
        ('nuclear_idx',     'Nuclear',          COLORS['nuclear']),
        ('renewable_idx',   'Renewables',       COLORS['renewables']),
        ('fossil_idx',      'Fossil imports',   COLORS['fossil']),
        ('dependency_idx',  'Dependency rate',  COLORS['dependency']),
    ]

    fig = go.Figure()
    for col, label, color in traces:
        fig.add_trace(go.Scatter(
            x=df['year'], y=df[col],
            name=label,
            line=dict(color=color, width=2.5),
        ))
    fig.add_hline(y=100, line_color='black', line_width=1, line_dash='dash', opacity=0.4)
    fig.update_layout(
        title='Germany Energy Mix — Indexed to 2005 = 100',
        xaxis_title=None,
        yaxis_title='Index (2005 = 100)',
        plot_bgcolor='white',
        yaxis=dict(gridcolor='#eeeeee'),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
    )
    return fig


def chart_germany_gap(df):
    """
    Area chart showing the cumulative nuclear loss vs cumulative renewable
    gain from 2005 baseline — visualises how much of the gap was filled.

    Expected df columns: year, nuclear_loss_cumulative, renewable_gain_cumulative
    """
    # nuclear_loss_cumulative is negative (nuclear declined); negate for display
    nuclear_loss = df['nuclear_loss_cumulative'].abs()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['year'], y=nuclear_loss,
        name='Cumulative nuclear loss',
        fill='tozeroy',
        line=dict(color=COLORS['nuclear'], width=2),
        fillcolor='rgba(122,122,122,0.25)',
    ))
    fig.add_trace(go.Scatter(
        x=df['year'], y=df['renewable_gain_cumulative'],
        name='Cumulative renewable gain',
        fill='tozeroy',
        line=dict(color=COLORS['renewables'], width=2),
        fillcolor='rgba(76,175,80,0.25)',
    ))
    fig.update_layout(
        title='Germany: Did Renewables Cover the Nuclear Gap?',
        xaxis_title=None,
        yaxis_title='Cumulative Change (million GWh)',
        plot_bgcolor='white',
        yaxis=dict(gridcolor='#eeeeee'),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
    )
    return fig


# ── Section 4: Four Country Archetypes ───────────────────────────────────────

def chart_archetype_renewable_share(df):
    """
    Line chart comparing renewable share over time for Germany, Italy,
    France, and Denmark — four different nuclear/renewable policy paths.

    Expected df columns: year, country, renewable_share
    """
    fig = go.Figure()
    for country, color in COUNTRY_COLORS.items():
        c_df = df[df['country'] == country]
        fig.add_trace(go.Scatter(
            x=c_df['year'], y=c_df['renewable_share'],
            name=country,
            line=dict(color=color, width=2.5),
        ))
    fig.update_layout(
        title='Renewable Share — Four Country Archetypes',
        xaxis_title=None,
        yaxis_title='Renewable Share (%)',
        plot_bgcolor='white',
        yaxis=dict(gridcolor='#eeeeee'),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
    )
    return fig


def chart_archetype_dependency(df):
    """
    Line chart comparing energy dependency rate over time for the same
    four countries.

    Expected df columns: year, country, dependency_rate
    """
    fig = go.Figure()
    for country, color in COUNTRY_COLORS.items():
        c_df = df[df['country'] == country]
        fig.add_trace(go.Scatter(
            x=c_df['year'], y=c_df['dependency_rate'],
            name=country,
            line=dict(color=color, width=2.5),
        ))
    fig.update_layout(
        title='Energy Dependency Rate — Four Country Archetypes',
        xaxis_title=None,
        yaxis_title='Dependency Rate (%)',
        plot_bgcolor='white',
        yaxis=dict(gridcolor='#eeeeee'),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
    )
    return fig


def chart_archetype_rank(df):
    """
    Line chart showing each archetype country's EU rank by renewable share
    per year — reveals whether their position improved or worsened relative
    to the rest of the EU.

    Expected df columns: year, country, rank
    """
    fig = go.Figure()
    for country, color in COUNTRY_COLORS.items():
        c_df = df[df['country'] == country]
        fig.add_trace(go.Scatter(
            x=c_df['year'], y=c_df['rank'],
            name=country,
            line=dict(color=color, width=2.5),
            mode='lines+markers',
            marker=dict(size=5),
        ))
    fig.update_layout(
        title='EU Rank by Renewable Share — Four Country Archetypes',
        xaxis_title=None,
        yaxis_title='EU Rank (1 = highest renewable share)',
        yaxis=dict(autorange='reversed', gridcolor='#eeeeee'),
        plot_bgcolor='white',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
    )
    return fig


# ── Section 5: EU Green Energy Reality Check ─────────────────────────────────

def chart_eu_renewable_share_trend(df):
    """
    Line chart of EU-wide renewable share (% of gross available energy)
    with a 3-year rolling average — the headline "is it actually growing?"
    answer.

    Expected df columns: year, renewable_share, rolling_share
    """
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['year'], y=df['renewable_share'],
        name='Annual share',
        line=dict(color=COLORS['renewables'], width=1, dash='dot'),
        opacity=0.6,
    ))
    fig.add_trace(go.Scatter(
        x=df['year'], y=df['rolling_share'],
        name='3-year rolling avg',
        line=dict(color=COLORS['renewables'], width=3),
    ))
    fig.update_layout(
        title='EU Renewable Share of Gross Available Energy',
        xaxis_title=None,
        yaxis_title='Renewable Share (%)',
        plot_bgcolor='white',
        yaxis=dict(gridcolor='#eeeeee', range=[5, 22]),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
    )
    return fig


def chart_absolute_fossil_consumption(df):
    """
    Line chart of absolute EU fossil fuel consumption in million GWh —
    separate from share, to show whether fossil use is declining in real
    terms or just being diluted by growth in total energy.

    Expected df columns: year, fossil_gwh_m
    """
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['year'], y=df['fossil_gwh_m'],
        name='Fossil consumption',
        line=dict(color=COLORS['fossil'], width=3),
        fill='tozeroy',
        fillcolor='rgba(196,115,58,0.15)',
    ))
    fig.update_layout(
        title='EU Absolute Fossil Fuel Consumption',
        xaxis_title=None,
        yaxis_title='Gross Available Energy (million GWh)',
        plot_bgcolor='white',
        yaxis=dict(gridcolor='#eeeeee'),
        showlegend=False,
    )
    return fig


def chart_country_scorecard(df):
    """
    Horizontal bar chart ranking all 27 countries by total renewable share
    growth from 2005 to 2024 — the "who actually moved" scorecard.

    Expected df columns: country, share_2005, share_2024, growth
    """
    df = df.sort_values('growth')
    colors = [COLORS['renewables'] if v >= 0 else COLORS['fossil'] for v in df['growth']]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df['growth'],
        y=df['country'],
        orientation='h',
        marker_color=colors,
        text=df['growth'].apply(lambda x: f"+{x:.1f}pp" if x >= 0 else f"{x:.1f}pp"),
        textposition='outside',
    ))
    fig.update_layout(
        title='Renewable Share Growth by Country (2005 → 2024)',
        xaxis_title='Growth (percentage points)',
        yaxis_title=None,
        plot_bgcolor='white',
        xaxis=dict(gridcolor='#eeeeee'),
        showlegend=False,
        height=700,
        margin=dict(l=120),
    )
    return fig
