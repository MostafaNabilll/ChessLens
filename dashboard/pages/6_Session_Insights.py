import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
import plotly.express as px
import pandas as pd
from utils import run_query, apply_styles, get_tc_default, get_username, style_chart

apply_styles()

MIN_SESSIONS = 3

st.header("Session Insights")
st.write("How does session length affect your performance? Should you stop after a few games or keep grinding?")
st.caption("A session is a run of games in the same time control with less than 30 minutes between them.")

username = get_username()

df = run_query("SELECT * FROM main_gold.gold_sessions WHERE username = ?", [username])

if df.empty:
    st.info("No games found for this account yet.")
    st.stop()

time_classes = df['time_class'].unique().tolist()
selected_tc = st.selectbox("Time Control", time_classes, index=get_tc_default(time_classes), key="session_tc")
df = df[df['time_class'] == selected_tc].copy()

st.divider()

cols = st.columns(4)
with cols[0]:
    st.metric("Total Sessions", len(df))
with cols[1]:
    st.metric("Avg Games/Session", f"{df['games_played'].mean():.1f}")
with cols[2]:
    st.metric("Avg Rating Change", f"{df['rating_delta'].mean():+.0f}")
with cols[3]:
    st.metric("Profitable Sessions", f"{(df['rating_delta'] > 0).mean():.0%}")

st.divider()

df['win_rate'] = df['wins'] / df['games_played']
df['length_bucket'] = pd.cut(
    df['games_played'],
    bins=[0, 2, 5, 10, 20, float('inf')],
    labels=['1-2', '3-5', '6-10', '11-20', '20+']
)

session_stats = df.groupby('length_bucket', observed=True).agg(
    sessions=('session_id', 'count'),
    avg_win_rate=('win_rate', 'mean'),
    avg_rating_delta=('rating_delta', 'mean')
).reset_index()

st.subheader("Win Rate by Session Length")
fig = px.bar(session_stats, x='length_bucket', y='avg_win_rate',
            text=session_stats.apply(lambda x: f"{x['avg_win_rate']:.0%} ({int(x['sessions'])} sessions)", axis=1),
            color='avg_win_rate',
            color_continuous_scale='RdYlGn',
            labels={'length_bucket': 'Games per Session', 'avg_win_rate': 'Avg Win Rate'})
fig.update_traces(textposition='outside', marker_line_width=0)
style_chart(fig, y_tickformat='.0%')
st.plotly_chart(fig, width='stretch')

st.divider()

st.subheader("Avg Rating Change by Session Length")
fig2 = px.bar(session_stats, x='length_bucket', y='avg_rating_delta',
            text=session_stats['avg_rating_delta'].apply(lambda x: f"{x:+.0f}"),
            color=session_stats['avg_rating_delta'].apply(lambda x: 'positive' if x >= 0 else 'negative'),
            color_discrete_map={'positive': '#2ecc71', 'negative': '#e74c3c'},
            labels={'length_bucket': 'Games per Session', 'avg_rating_delta': 'Avg Rating Change'})
fig2.update_traces(textposition='outside', marker_line_width=0)
style_chart(fig2, showlegend=False)
st.plotly_chart(fig2, width='stretch')

reliable = session_stats[session_stats['sessions'] >= MIN_SESSIONS]
if len(reliable) >= 2:
    best = reliable.loc[reliable['avg_rating_delta'].idxmax()]
    worst = reliable.loc[reliable['avg_rating_delta'].idxmin()]
    st.success(f"Best session length: **{best['length_bucket']}** games (avg {best['avg_rating_delta']:+.0f} rating)")
    st.warning(f"Worst session length: **{worst['length_bucket']}** games (avg {worst['avg_rating_delta']:+.0f} rating)")
else:
    st.info(f"Play more sessions to unlock the best and worst session length (each length needs {MIN_SESSIONS}+ sessions).")