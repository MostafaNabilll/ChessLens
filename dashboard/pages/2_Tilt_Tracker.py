import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
import plotly.express as px
from utils import run_query, apply_styles, get_username, style_chart

apply_styles()

st.header("Tilt Tracker")
st.write("Does losing make you lose more? This page tracks how consecutive losses affect your next game.")

username = get_username()

df1 = run_query("""
    SELECT
        is_tilted,
        COUNT(*) AS games,
        AVG(CASE WHEN result = 'win' THEN 1 ELSE 0 END) AS win_rate
    FROM main_gold.gold_tilt_analysis
    WHERE username = ?
    GROUP BY 1
    ORDER BY 1
""", [username])

if df1.empty:
    st.info("No games found for this account yet.")
    st.stop()

st.caption("A game counts as tilted when you lost the 3 or more games right before it.")

cols = st.columns(2)
for col, tilted in zip(cols, [False, True]):
    row = df1[df1['is_tilted'] == tilted]
    label = "Tilted (after 3+ losses)" if tilted else "Not tilted"
    with col:
        if row.empty:
            st.metric(label, "0 games")
        else:
            row = row.iloc[0]
            st.metric(label, f"{int(row['games'])} games", delta=f"Win rate {row['win_rate']:.1%}", delta_color="off")

st.divider()

st.subheader("Win Rate by Loss Streak")
st.write("Each bar shows your win rate after N consecutive losses.")

df2 = run_query("""
    SELECT
        consecutive_losses_before,
        COUNT(*) AS games,
        AVG(CASE WHEN result = 'win' THEN 1 ELSE 0 END) AS win_rate
    FROM main_gold.gold_tilt_analysis
    WHERE username = ?
    GROUP BY 1
    ORDER BY 1
""", [username])

fig = px.bar(df2, x='consecutive_losses_before', y='win_rate',
            text=df2.apply(lambda x: f"{x['win_rate']:.0%} ({int(x['games'])} games)", axis=1),
            labels={'consecutive_losses_before': 'Consecutive Losses Before Game', 'win_rate': 'Win Rate'},
            color='win_rate',
            color_continuous_scale='RdYlGn')
fig.update_traces(textposition='outside', marker_line_width=0)
style_chart(fig, height=450, y_tickformat='.0%', showlegend=False)
fig.update_layout(xaxis=dict(dtick=1))
st.plotly_chart(fig, width='stretch')

tilted_wr = df1[df1['is_tilted'] == True]['win_rate'].values
normal_wr = df1[df1['is_tilted'] == False]['win_rate'].values
if len(tilted_wr) == 0:
    st.info("You haven't had a 3-game losing streak yet, so there's no tilt to measure.")
elif len(normal_wr) > 0:
    diff = tilted_wr[0] - normal_wr[0]
    if diff > 0:
        st.success(f"You actually play **better** after losing streaks ({diff:+.1%}). No tilt detected.")
    else:
        st.warning(f"Your win rate drops by **{abs(diff):.1%}** after 3+ losses in a row. Consider taking a break at that point.")