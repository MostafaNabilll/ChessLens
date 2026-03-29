import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
import plotly.express as px
import pandas as pd
from utils import run_query, apply_styles, get_tc_default, get_username, style_chart

apply_styles()

st.header("Overview")
st.write("Quick snapshot of your chess performance across all time controls.")

username = get_username()

df = run_query(f"SELECT * FROM main_gold.gold_time_control_comparison WHERE username = '{username}'")

if df.empty:
    st.warning("No data found for this user.")
    st.stop()

# Rating cards
cols = st.columns(len(df))
for i, row in df.iterrows():
    with cols[i]:
        peak_diff = row['current_rating'] - row['peak_rating']
        if peak_diff >= 0:
            delta_val = "At Peak!"
        else:
            delta_val = f"{int(peak_diff)} from peak"
        st.metric(
            label=f'{row["time_class"].title()} Rating',
            value=int(row['current_rating']),
            delta=delta_val,
            delta_color="normal"
        )

total = df['total_games'].sum()
overall_wr = (df['win_rate'] * df['total_games']).sum() / total

cols = st.columns([1, 1, 1])

with cols[0]:
    st.metric(label="Total Games", value=total, delta=f"{overall_wr:.1%} win rate")

with cols[1]:
    longest_win = run_query(f"""
        SELECT MAX(streak) as longest FROM (
            SELECT COUNT(*) as streak
            FROM (
                SELECT result,
                    SUM(CASE WHEN result != 'win' THEN 1 ELSE 0 END) 
                    OVER (ORDER BY end_at) as grp
                FROM main_silver.silver_games
                WHERE username = '{username}'
            )
            WHERE result = 'win'
            GROUP BY grp
        )
    """)['longest'].iloc[0]
    if pd.isna(longest_win):
        longest_win = 0
    st.metric("Longest Win Streak", f"{int(longest_win)} games", delta=f"{int(longest_win)} in a row")

with cols[2]:
    longest_loss = run_query(f"""
        SELECT MAX(streak) as longest FROM (
            SELECT COUNT(*) as streak
            FROM (
                SELECT result,
                    SUM(CASE WHEN result != 'loss' THEN 1 ELSE 0 END) 
                    OVER (ORDER BY end_at) as grp
                FROM main_silver.silver_games
                WHERE username = '{username}'
            )
            WHERE result = 'loss'
            GROUP BY grp
        )
    """)['longest'].iloc[0]
    if pd.isna(longest_loss):
        longest_loss = 0
    st.metric("Longest Loss Streak", f"{int(longest_loss)} games", delta=f"-{int(longest_loss)} in a row")

# Win Rate by Color
st.subheader("Win Rate by Color")
df_color = run_query(f"""
    SELECT player_color, COUNT(*) as games,
    AVG(CASE WHEN result = 'win' THEN 1 ELSE 0 END) as win_rate
    FROM main_silver.silver_games 
    WHERE username = '{username}'
    GROUP BY 1
""")

if not df_color.empty and len(df_color) == 2:
    cols = st.columns(2)
    with cols[0]:
        white_row = df_color[df_color['player_color'] == 'white'].iloc[0]
        st.metric("White", f"{white_row['win_rate']:.1%}", delta=f"{int(white_row['games'])} games", delta_color="off")
    with cols[1]:
        black_row = df_color[df_color['player_color'] == 'black'].iloc[0]
        st.metric("Black", f"{black_row['win_rate']:.1%}", delta=f"{int(black_row['games'])} games", delta_color="off")

st.divider()

st.subheader("Rating Progression")

time_classes_list = run_query(f"SELECT DISTINCT time_class FROM main_silver.silver_games WHERE username = '{username}'")['time_class'].tolist()

if time_classes_list:
    rating_tc = st.selectbox("Time Control", 
        time_classes_list, 
        index=get_tc_default(time_classes_list),
        key="rating_tc")

    df_rating = run_query(f"""
        SELECT end_at, player_rating 
        FROM main_silver.silver_games 
        WHERE time_class = '{rating_tc}'
        AND username = '{username}'
        ORDER BY end_at
    """)

    if not df_rating.empty:
        fig = px.line(df_rating, x='end_at', y='player_rating',
                    labels={'end_at': 'Date', 'player_rating': 'Rating'})
        style_chart(fig)
        st.plotly_chart(fig, width='stretch')

st.divider()

# Games distribution chart
st.subheader("Games by Time Control")
fig = px.bar(df, x='time_class', y='total_games',
            text='total_games',
            labels={'time_class': 'Time Control', 'total_games': 'Games Played'},
            color_discrete_sequence=['#4C78A8'])  
fig.update_traces(textposition='outside', marker_line_width=0)
style_chart(fig)
st.plotly_chart(fig, use_container_width=True)

# Timeout rate comparison
st.subheader("Timeout Loss Rate")
fig2 = px.bar(df, x='time_class', y='timeout_loss_rate',
            text=df['timeout_loss_rate'].apply(lambda x: f"{x:.1%}"),
            labels={'time_class': 'Time Control', 'timeout_loss_rate': 'Timeout Loss Rate'},
            color_discrete_sequence=['#ff6b6b'])
fig2.update_traces(textposition='outside')
style_chart(fig2, height=350, y_tickformat='.0%')
st.plotly_chart(fig2, use_container_width=True)