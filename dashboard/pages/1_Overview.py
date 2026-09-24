import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
import plotly.express as px
import pandas as pd
from utils import run_query, apply_styles, get_tc_default, get_username, style_chart, DEFAULT_USERNAME

apply_styles()

username = get_username()

st.header("Overview")
st.write("Quick snapshot of your chess performance across all time controls.")

if username == DEFAULT_USERNAME:
    st.info(
        "You're viewing a demo account with real games. Click **Analyze your own games** "
        "in the sidebar to run ChessLens on any chess.com username."
    )

df = run_query("SELECT * FROM main_gold.gold_time_control_comparison WHERE username = ?", [username])

if df.empty:
    st.info("No games found for this account yet. Play a few games on chess.com, then hit Refresh data.")
    st.stop()

# Rating cards
cols = st.columns(len(df))
for i, row in df.reset_index(drop=True).iterrows():
    with cols[i]:
        peak_diff = row['current_rating'] - row['peak_rating']
        delta_val = "At peak" if peak_diff >= 0 else f"{int(peak_diff)} from peak"
        st.metric(
            label=f'{row["time_class"].title()} Rating',
            value=int(row['current_rating']),
            delta=delta_val,
            delta_color="normal"
        )

total = int(df['total_games'].sum())
overall_wr = (df['win_rate'] * df['total_games']).sum() / total

streak_query = """
    SELECT MAX(streak) AS longest FROM (
        SELECT COUNT(*) AS streak
        FROM (
            SELECT result,
                SUM(CASE WHEN result != ? THEN 1 ELSE 0 END) OVER (ORDER BY end_at) AS grp
            FROM main_silver.silver_games
            WHERE username = ?
        )
        WHERE result = ?
        GROUP BY grp
    )
"""


def longest_streak(result):
    value = run_query(streak_query, [result, username, result])['longest'].iloc[0]
    return 0 if pd.isna(value) else int(value)


longest_win = longest_streak('win')
longest_loss = longest_streak('loss')

cols = st.columns(3)
with cols[0]:
    st.metric("Total Games", f"{total:,}", delta=f"{overall_wr:.1%} win rate", delta_color="off")
with cols[1]:
    st.metric("Longest Win Streak", f"{longest_win} games")
with cols[2]:
    st.metric("Longest Loss Streak", f"{longest_loss} games")

# Win rate by color
st.subheader("Win Rate by Color")
df_color = run_query("""
    SELECT player_color, COUNT(*) AS games,
    AVG(CASE WHEN result = 'win' THEN 1 ELSE 0 END) AS win_rate
    FROM main_silver.silver_games 
    WHERE username = ?
    GROUP BY 1
""", [username])

cols = st.columns(2)
for col, color in zip(cols, ['white', 'black']):
    row = df_color[df_color['player_color'] == color]
    with col:
        if row.empty:
            st.metric(color.title(), "No games")
        else:
            row = row.iloc[0]
            st.metric(color.title(), f"{row['win_rate']:.1%}", delta=f"{int(row['games'])} games", delta_color="off")

st.divider()

st.subheader("Rating Progression")
time_classes_list = run_query(
    "SELECT DISTINCT time_class FROM main_silver.silver_games WHERE username = ?", [username]
)['time_class'].tolist()

rating_tc = st.selectbox("Time Control", time_classes_list, index=get_tc_default(time_classes_list), key="rating_tc")

df_rating = run_query("""
    SELECT end_at, player_rating 
    FROM main_silver.silver_games 
    WHERE time_class = ?
    AND username = ?
    ORDER BY end_at
""", [rating_tc, username])

if len(df_rating) < 2:
    st.info("Not enough games in this time control to draw a rating curve yet.")
else:
    fig = px.line(df_rating, x='end_at', y='player_rating', labels={'end_at': 'Date', 'player_rating': 'Rating'})
    style_chart(fig)
    st.plotly_chart(fig, width='stretch')

st.divider()

st.subheader("Games by Time Control")
fig = px.bar(df, x='time_class', y='total_games',
            text='total_games',
            labels={'time_class': 'Time Control', 'total_games': 'Games Played'},
            color_discrete_sequence=['#4C78A8'])
fig.update_traces(textposition='outside', marker_line_width=0)
style_chart(fig)
st.plotly_chart(fig, width='stretch')

st.subheader("Timeout Loss Rate")
st.caption("Share of games in each time control that you lost on the clock.")
fig2 = px.bar(df, x='time_class', y='timeout_loss_rate',
            text=df['timeout_loss_rate'].apply(lambda x: f"{x:.1%}"),
            labels={'time_class': 'Time Control', 'timeout_loss_rate': 'Timeout Loss Rate'},
            color_discrete_sequence=['#ff6b6b'])
fig2.update_traces(textposition='outside')
style_chart(fig2, height=350, y_tickformat='.0%')
st.plotly_chart(fig2, width='stretch')