import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
import plotly.express as px
from utils import run_query, apply_styles, get_tc_default, get_username, style_chart

apply_styles()

st.header("Opening Lab")
st.write("Track how your openings perform over time and spot what's improving or declining.")
st.caption("An opening shows up here once you play it at least 5 times in a month. Trends compare each month to the previous one (a change of more than 5 points counts).")

username = get_username()

df = run_query("SELECT * FROM main_gold.gold_opening_trends WHERE username = ?", [username])

if df.empty:
    st.info("No opening has reached 5 games in a single month yet. Keep playing and check back.")
    st.stop()

col1, col2 = st.columns(2)
with col1:
    time_classes = df['time_class'].unique().tolist()
    selected_tc = st.selectbox("Time Control", time_classes, index=get_tc_default(time_classes), key="opening_tc")
with col2:
    trend_filter = st.selectbox("Trend", ["All", "improving", "declining", "stable"], key="opening_trend")

df = df[df['time_class'] == selected_tc]
df_trends = df[df['trend'] != 'new']

st.divider()

st.subheader("Win Rate Over Time")

if trend_filter != "All" and not df_trends.empty:
    latest_month = df_trends['month'].max()
    trending = df_trends[(df_trends['month'] == latest_month) & (df_trends['trend'] == trend_filter)]['opening_family'].unique()
    df_chart = df[df['opening_family'].isin(trending)]
else:
    df_chart = df

all_openings = df_chart.groupby('opening_family')['games_played'].sum().sort_values(ascending=False).index.tolist()

if not all_openings:
    st.info("No openings match this trend filter.")
else:
    selected_openings = st.multiselect("Select Openings", all_openings, default=all_openings[:5])
    df_top = df_chart[df_chart['opening_family'].isin(selected_openings)]
    if df_top.empty:
        st.info("Pick at least one opening to plot.")
    else:
        fig = px.line(df_top, x='month', y='win_rate', color='opening_family',
                    markers=True,
                    labels={'month': 'Month', 'win_rate': 'Win Rate', 'opening_family': 'Opening'})
        style_chart(fig, height=450, y_tickformat='.0%')
        fig.update_layout(legend=dict(orientation='h', yanchor='bottom', y=-0.35))
        st.plotly_chart(fig, width='stretch')

st.divider()

st.subheader("Latest Month")

if df_trends.empty:
    st.info("Trends need at least two months of 5+ games with the same opening in this time control.")
    st.stop()

latest_month = df_trends['month'].max()
df_latest = df_trends[df_trends['month'] == latest_month].sort_values('games_played', ascending=False)
st.caption(f"Openings played in {latest_month:%B %Y}, compared to the month before.")

if trend_filter != "All":
    df_latest = df_latest[df_latest['trend'] == trend_filter]

if df_latest.empty:
    st.info("No openings match this trend filter.")
else:
    display_df = df_latest[['opening_family', 'games_played', 'win_rate', 'prev_month_win_rate', 'avg_opponent_rating', 'trend']].copy()
    display_df['win_rate'] = display_df['win_rate'].apply(lambda x: f"{x:.0%}")
    display_df['prev_month_win_rate'] = display_df['prev_month_win_rate'].apply(lambda x: f"{x:.0%}")
    display_df['avg_opponent_rating'] = display_df['avg_opponent_rating'].apply(lambda x: f"{x:.0f}")
    display_df['trend'] = display_df['trend'].str.title()
    display_df.columns = ['Opening', 'Games', 'Win Rate', 'Previous Month', 'Avg Opponent', 'Trend']
    st.dataframe(display_df, width='stretch', hide_index=True)

    improving = (df_latest['trend'] == 'improving').sum()
    declining = (df_latest['trend'] == 'declining').sum()
    if improving:
        st.success(f"{improving} opening(s) improving")
    if declining:
        st.warning(f"{declining} opening(s) declining")