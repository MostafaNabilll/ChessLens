import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
import plotly.express as px
from utils import run_query, apply_styles, get_tc_default, get_username, style_chart

apply_styles()

MIN_GAMES = 5
BUCKET_LABELS = {
    'much_lower': '200+ lower',
    'lower': '50 to 200 lower',
    'equal': 'Within 50',
    'higher': '50 to 200 higher',
    'much_higher': '200+ higher',
}

st.header("Know Your Opponent")
st.write("How do you perform against weaker, equal, and stronger opponents?")
st.caption("Opponents are grouped by their rating relative to yours at the time of the game.")

username = get_username()

df = run_query("SELECT * FROM main_gold.gold_opponent_analysis WHERE username = ?", [username])

if df.empty:
    st.info("No games found for this account yet.")
    st.stop()

time_classes = df['time_class'].unique().tolist()
selected_tc = st.selectbox("Time Control", time_classes, index=get_tc_default(time_classes), key="opponent_tc")
df = df[df['time_class'] == selected_tc].copy()

df['bucket_label'] = df['rating_bucket'].map(BUCKET_LABELS)
df['order'] = df['rating_bucket'].map({k: i for i, k in enumerate(BUCKET_LABELS)})
df = df.sort_values('order')

st.divider()

st.subheader("Win Rate by Opponent Strength")
fig = px.bar(df, x='bucket_label', y='win_rate',
            text=df.apply(lambda x: f"{x['win_rate']:.0%} ({int(x['games_played'])} games)", axis=1),
            color='win_rate',
            color_continuous_scale='RdYlGn',
            category_orders={'bucket_label': list(BUCKET_LABELS.values())},
            labels={'bucket_label': 'Opponent Rating vs Yours', 'win_rate': 'Win Rate'})
fig.update_traces(textposition='outside', marker_line_width=0)
style_chart(fig, height=450, y_tickformat='.0%')
st.plotly_chart(fig, width='stretch')

st.divider()

st.subheader("Upset Wins")
st.caption("An upset is a win against someone the rating system expected you to lose to.")
higher_df = df[df['rating_bucket'].isin(['higher', 'much_higher'])]
higher_upsets = int(higher_df['upset_wins'].sum())
higher_games = int(higher_df['games_played'].sum())

cols = st.columns(2)
with cols[0]:
    st.metric("Total Upset Wins", int(df['upset_wins'].sum()))
with cols[1]:
    if higher_games > 0:
        st.metric("Win Rate vs Stronger Opponents", f"{higher_upsets / higher_games:.0%}", delta=f"{higher_games} games", delta_color="off")
    else:
        st.metric("Win Rate vs Stronger Opponents", "No games")



def describe(bucket):
    if bucket == 'equal':
        return "rated within 50 of you"
    return f"rated {BUCKET_LABELS[bucket]} than you"


reliable = df[df['games_played'] >= MIN_GAMES]
if len(reliable) >= 2:
    best = reliable.loc[reliable['win_rate'].idxmax()]
    worst = reliable.loc[reliable['win_rate'].idxmin()]
    st.success(f"Strongest against opponents **{describe(best['rating_bucket'])}** ({best['win_rate']:.0%} win rate)")
    st.error(f"Weakest against opponents **{describe(worst['rating_bucket'])}** ({worst['win_rate']:.0%} win rate)")