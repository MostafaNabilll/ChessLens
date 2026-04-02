import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
import plotly.express as px
import pandas as pd
from utils import run_query, apply_styles, get_tc_default, get_username, style_chart

apply_styles()

st.header("When To Play")
st.write("Discover when you play your best chess based on time of day and day of week.")

username = get_username()

df = run_query("SELECT * FROM main_gold.gold_time_of_day WHERE username = ?", [username])

if df.empty:
    st.warning("No data found for this filter.")
    st.stop()

# Time class filter
time_classes = df['time_class'].unique().tolist()
options = ["All"] + time_classes
selected_tc = st.selectbox("Time Control", options, index=get_tc_default(options), key="when_tc")

if selected_tc != "All":
    df = df[df['time_class'] == selected_tc]

st.divider()

# Heatmap: day of week vs hour bucket
heatmap_data = df.groupby(['day_of_week', 'hour_bucket']).agg(
    win_rate=('win_rate', 'mean'),
    games=('games_played', 'sum')
).reset_index()

day_names = {0: 'Sunday', 1: 'Monday', 2: 'Tuesday', 3: 'Wednesday', 4: 'Thursday', 5: 'Friday', 6: 'Saturday'}
heatmap_data['day_name'] = heatmap_data['day_of_week'].map(day_names)

bucket_order = ['morning', 'afternoon', 'evening', 'night']
day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

pivot = heatmap_data.pivot_table(index='day_name', columns='hour_bucket', values='win_rate')
pivot = pivot.reindex(index=day_order, columns=bucket_order)

st.subheader("Win Rate Heatmap")
fig = px.imshow(pivot,
                color_continuous_scale='RdYlGn',
                text_auto='.0%',
                labels={'color': 'Win Rate'},
                aspect='auto')
fig.update_layout(
    height=400,
    margin=dict(t=30, b=30),
    font=dict(size=13),
    xaxis_title="Time of Day",
    yaxis_title=""
)
st.plotly_chart(fig, use_container_width=True)

# Best and worst times
st.divider()
best = heatmap_data.loc[heatmap_data['win_rate'].idxmax()]
worst = heatmap_data.loc[heatmap_data['win_rate'].idxmin()]

cols = st.columns(2)
with cols[0]:
    st.success(f"Best: {best['day_name']} {best['hour_bucket']} ({best['win_rate']:.0%} over {int(best['games'])} games)")
with cols[1]:
    st.error(f"Worst: {worst['day_name']} {worst['hour_bucket']} ({worst['win_rate']:.0%} over {int(worst['games'])} games)")

