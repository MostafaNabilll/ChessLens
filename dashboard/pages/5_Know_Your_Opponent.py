import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
import plotly.express as px
import pandas as pd
from utils import run_query, apply_styles, get_tc_default, get_username, style_chart

apply_styles()

st.header("Know Your Opponent")
st.write("How do you perform against different strength opponents?")

username = get_username()

df = run_query(f"SELECT * FROM main_gold.gold_opponent_analysis WHERE username = '{username}'")

if df.empty:
    st.warning("No data found for this filter.")
    st.stop()

# Filter
time_classes = df['time_class'].unique().tolist()
selected_tc = st.selectbox("Time Control", time_classes, index=get_tc_default(time_classes), key="opponent_tc")
df = df[df['time_class'] == selected_tc]

st.divider()

# Order buckets logically
bucket_order = ['much_lower', 'lower', 'equal', 'higher', 'much_higher']
df['rating_bucket'] = pd.Categorical(df['rating_bucket'], categories=bucket_order, ordered=True)
df = df.sort_values('rating_bucket')

# Win rate by rating bucket
st.subheader("Win Rate by Opponent Strength")
fig = px.bar(df, x='rating_bucket', y='win_rate',
            text=df.apply(lambda x: f"{x['win_rate']:.0%} ({int(x['games_played'])} games(s))", axis=1),
            color='win_rate',
            color_continuous_scale='RdYlGn',
            labels={'rating_bucket': 'Opponent Strength', 'win_rate': 'Win Rate'})
fig.update_traces(textposition='outside', marker_line_width=0)
style_chart(fig, height=450, y_tickformat='.0%')
st.plotly_chart(fig, width='stretch')

st.divider()

# Upset stats
st.subheader("Upset Wins")
total_upsets = int(df['upset_wins'].sum())
higher_games = df[df['rating_bucket'].isin(['higher', 'much_higher'])]['games_played'].sum()

cols = st.columns(2)
with cols[0]:
    st.metric("Total Upset Wins", total_upsets)
with cols[1]:
    higher_df = df[df['rating_bucket'].isin(['higher', 'much_higher'])]
    higher_upsets = int(higher_df['upset_wins'].sum())
    higher_games = int(higher_df['games_played'].sum())
    if higher_games > 0:
        overall_upset_rate = higher_upsets / higher_games
        st.metric("Upset Rate vs Stronger Opponents", f"{overall_upset_rate:.0%}")

# Takeaway
if not df.empty:
    best_bucket = df.loc[df['win_rate'].idxmax()]
    worst_bucket = df.loc[df['win_rate'].idxmin()]
    st.success(f"Strongest against **{best_bucket['rating_bucket']}** rated opponents ({best_bucket['win_rate']:.0%} win rate)")
    st.error(f"Weakest against **{worst_bucket['rating_bucket']}** rated opponents ({worst_bucket['win_rate']:.0%} win rate)")
