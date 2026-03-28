import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
import plotly.express as px
import pandas as pd
from utils import run_query, apply_styles, get_tc_default

apply_styles()

st.header("Opening Lab")
st.write("Track how your openings perform over time and spot what's improving or declining.")

df = run_query("SELECT * FROM main_gold.gold_opening_trends")

# Filters
col1, col2 = st.columns(2)
with col1:
    time_classes = df['time_class'].unique().tolist()
    selected_tc = st.selectbox("Time Control", time_classes, index=get_tc_default(time_classes), key="opening_tc")
with col2:
    trend_filter = st.selectbox("Trend", ["All", "improving", "declining", "stable"], key="opening_trend")

# Filter time class for everything
df = df[df['time_class'] == selected_tc]
df = df[df['trend'] != 'new']


st.divider()

# Filter openings by trend
if trend_filter != "All":
    latest_month = df['month'].max()
    trending_openings = df[(df['month'] == latest_month) & (df['trend'] == trend_filter)]['opening_family'].unique().tolist()
    df_chart = df[df['opening_family'].isin(trending_openings)]
else:
    df_chart = df

all_openings = df_chart.groupby('opening_family')['games_played'].sum().sort_values(ascending=False).index.tolist()
selected_openings = st.multiselect("Select Openings", all_openings, default=all_openings[:5])
df_top = df_chart[df_chart['opening_family'].isin(selected_openings)]

st.subheader("Win Rate Over Time")
if not df_top.empty:
    fig = px.line(df_top, x='month', y='win_rate', color='opening_family',
                markers=True,
                labels={'month': 'Month', 'win_rate': 'Win Rate', 'opening_family': 'Opening'})
    fig.update_layout(
        yaxis_tickformat='.0%',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        height=450,
        yaxis=dict(gridcolor='rgba(128,128,128,0.2)'),
        margin=dict(t=30, b=50),
        font=dict(size=13),
        legend=dict(orientation='h', yanchor='bottom', y=-0.3)
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No data for the selected filters.")

st.divider()

# Table uses trend filter
st.subheader("Opening Trends")
latest_month = df['month'].max()
df_latest = df[df['month'] == latest_month].sort_values('games_played', ascending=False)

if trend_filter != "All":
    df_latest = df_latest[df_latest['trend'] == trend_filter]

if not df_latest.empty:
    display_df = df_latest[['opening_family', 'games_played', 'win_rate', 'avg_opponent_rating', 'trend']].copy()
    display_df['win_rate'] = display_df['win_rate'].apply(lambda x: f"{x:.0%}")
    display_df['avg_opponent_rating'] = display_df['avg_opponent_rating'].apply(lambda x: f"{x:.0f}")
    display_df.columns = ['Opening', 'Games', 'Win Rate', 'Avg Opponent', 'Trend']
    st.dataframe(display_df, use_container_width=True, hide_index=True)
else:
    st.info("No openings match this trend filter.")

# Takeaway
improving = df_latest[df_latest['trend'] == 'improving'] if 'trend' in df_latest.columns else []
declining = df_latest[df_latest['trend'] == 'declining'] if 'trend' in df_latest.columns else []
if len(improving) > 0:
    st.success(f"{len(improving)} opening(s) improving this month")
if len(declining) > 0:
    st.warning(f"{len(declining)} opening(s) declining this month")
