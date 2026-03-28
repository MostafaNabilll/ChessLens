import streamlit as st

st.set_page_config(page_title="ChessLens", page_icon="♟️", layout="wide")

overview = st.Page("pages/1_Overview.py", title="Overview", default=True)
tilt = st.Page("pages/2_Tilt_Tracker.py", title="Tilt Tracker")
when = st.Page("pages/3_When_To_Play.py", title="When To Play")
opening = st.Page("pages/4_Opening_Lab.py", title="Opening Lab")
opponent = st.Page("pages/5_Know_Your_Opponent.py", title="Know Your Opponent")
session = st.Page("pages/6_Session_Insights.py", title="Session Insights")

pg = st.navigation([overview, tilt, when, opening, opponent, session])
pg.run()