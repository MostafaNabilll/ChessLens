import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
import plotly.express as px
import pandas as pd
from utils import run_query, apply_styles, get_tc_default, get_username

apply_styles()

st.header("Session Insights")
st.write("How does session length affect your performance? Should you stop after a few games or keep grinding?")

username = get_username()

df = run_query(f"SELECT * FROM main_gold.gold_sessions WHERE username = '{username}'")

if df.empty:
    st.warning("No data found for this filter.")
    st.stop()

# Filter
time_classes = df['time_class'].unique().tolist()
selected_tc = st.selectbox("Time Control", time_classes, index=get_tc_default(time_classes), key="session_tc")
df = df[df['time_class'] == selected_tc]

st.divider()

# Key metrics
cols = st.columns(4)
with cols[0]:
    st.metric("Total Sessions", len(df))
with cols[1]:
    avg_games = df['games_played'].mean()
    st.metric("Avg Games/Session", f"{avg_games:.1f}")
with cols[2]:
    avg_delta = df['rating_delta'].mean()
    st.metric("Avg Rating Change", f"{avg_delta:+.0f}", delta_color="normal")
with cols[3]:
    positive_sessions = (df['rating_delta'] > 0).sum() / len(df) if len(df) > 0 else 0
    st.metric("Profitable Sessions", f"{positive_sessions:.0%}")

st.divider()

# Win rate by session length
st.subheader("Win Rate by Session Length")
df['win_rate'] = df['wins'] / df['games_played']
df['length_bucket'] = pd.cut(df['games_played'], 
                            bins=[0, 2, 5, 10, 20, 100], 
                            labels=['1-2', '3-5', '6-10', '11-20', '20+'])

session_stats = df.groupby('length_bucket', observed=True).agg(
    sessions=('session_id', 'count'),
    avg_win_rate=('win_rate', 'mean'),
    avg_rating_delta=('rating_delta', 'mean')
).reset_index()

fig = px.bar(session_stats, x='length_bucket', y='avg_win_rate',
            text=session_stats.apply(lambda x: f"{x['avg_win_rate']:.0%} ({int(x['sessions'])}s)", axis=1),
            color='avg_win_rate',
            color_continuous_scale='RdYlGn',
            labels={'length_bucket': 'Games per Session', 'avg_win_rate': 'Avg Win Rate'})
fig.update_traces(textposition='outside', marker_line_width=0)
fig.update_layout(
    yaxis_tickformat='.0%',
    plot_bgcolor='rgba(0,0,0,0)',
    paper_bgcolor='rgba(0,0,0,0)',
    height=400,
    coloraxis_showscale=False,
    yaxis=dict(gridcolor='rgba(128,128,128,0.2)'),
    margin=dict(t=30, b=50),
    font=dict(size=13)
)
st.plotly_chart(fig, width='stretch')

st.divider()

# Rating change by session length
st.subheader("Avg Rating Change by Session Length")
fig2 = px.bar(session_stats, x='length_bucket', y='avg_rating_delta',
            text=session_stats['avg_rating_delta'].apply(lambda x: f"{x:+.0f}"),
            color=session_stats['avg_rating_delta'].apply(lambda x: 'positive' if x >= 0 else 'negative'),
            color_discrete_map={'positive': '#2ecc71', 'negative': '#e74c3c'},
            labels={'length_bucket': 'Games per Session', 'avg_rating_delta': 'Avg Rating Change'})
fig2.update_traces(textposition='outside', marker_line_width=0)
fig2.update_layout(
    plot_bgcolor='rgba(0,0,0,0)',
    paper_bgcolor='rgba(0,0,0,0)',
    height=400,
    showlegend=False,
    yaxis=dict(gridcolor='rgba(128,128,128,0.2)'),
    margin=dict(t=30, b=50),
    font=dict(size=13)
)
st.plotly_chart(fig2, width='stretch')

# Takeaway
best_length = session_stats.loc[session_stats['avg_rating_delta'].idxmax()]
worst_length = session_stats.loc[session_stats['avg_rating_delta'].idxmin()]
st.success(f"Best session length: **{best_length['length_bucket']}** games (avg {best_length['avg_rating_delta']:+.0f} rating)")
st.warning(f"Worst session length: **{worst_length['length_bucket']}** games (avg {worst_length['avg_rating_delta']:+.0f} rating)")