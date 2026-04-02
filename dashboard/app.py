import streamlit as st
import requests
import subprocess
import sys
import os
import shutil
import duckdb
from pathlib import Path

st.set_page_config(page_title="ChessLens", page_icon="♟️", layout="wide")

DB_PATH = str(Path(__file__).parent.parent / "data" / "chesslens.duckdb")
DEFAULT_USERNAME = "maxime-ana"


def run_pipeline(username, backfill=False):
    """Run ingestion and dbt for a given username."""
    args = [
        sys.executable,
        str(Path(__file__).parent.parent / "ingestion" / "extract.py"),
        "--username", username
    ]
    if backfill:
        args.append("--backfill")
    
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        return False, f"Ingestion failed: {result.stderr}"
    
    dbt_path = shutil.which("dbt") or str(Path(sys.executable).parent / "dbt")
    dbt_project = str(Path(__file__).parent.parent / "dbt_chesslens")
    result = subprocess.run([
        dbt_path, "build", "--full-refresh",
        "--project-dir", dbt_project,
        "--profiles-dir", dbt_project
    ], capture_output=True, text=True, cwd=dbt_project)
    
    if result.returncode != 0:
        return False, f"dbt failed: {result.stderr}\n{result.stdout}"
    
    return True, None


def check_user_exists(username):
    """Check if a username already has data in the DB."""
    if not os.path.exists(DB_PATH):
        return False
    try:
        conn = duckdb.connect(DB_PATH, read_only=True)
        cnt = conn.execute(
            "SELECT COUNT(*) FROM raw_games WHERE username = ?",
            [username]
        ).fetchone()[0]
        conn.close()
        return cnt > 0
    except duckdb.Error:
        return False


def ensure_data(username):
    """Make sure data exists for the username, run pipeline if not."""
    if not check_user_exists(username):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        with st.spinner(f"Pulling games for {username}... This may take a minute."):
            ok, err = run_pipeline(username, backfill=True)
        if not ok:
            st.error(err)
            return False
    return True


# Default to demo user, allow switching
if 'chess_username' not in st.session_state:
    st.session_state.chess_username = DEFAULT_USERNAME

# Handle "enter new username" mode
if st.session_state.get('switching_user'):
    st.title("ChessLens")
    st.write("Enter a chess.com username to analyze.")
    
    username = st.text_input("Chess.com Username")
    
    if st.button("Analyze"):
        if not username:
            st.error("Please enter a username.")
        else:
            with st.spinner("Checking username..."):
                resp = requests.get(
                    f"https://api.chess.com/pub/player/{username.lower()}",
                    headers={"User-Agent": "ChessLens/1.0"}
                )
            
            if resp.status_code != 200:
                st.error(f"Username '{username}' not found on chess.com.")
            else:
                st.session_state.chess_username = username.lower()
                st.session_state.switching_user = False
                if ensure_data(username.lower()):
                    st.rerun()
    
    if st.button("Back to demo"):
        st.session_state.chess_username = DEFAULT_USERNAME
        st.session_state.switching_user = False
        st.rerun()

else:
    # Make sure data exists for current user
    if not ensure_data(st.session_state.chess_username):
        st.stop()
    
    st.sidebar.title("ChessLens")
    st.sidebar.caption(f"Player: {st.session_state.chess_username}")
    
    if st.sidebar.button("Refresh Data"):
        with st.spinner("Updating games..."):
            ok, err = run_pipeline(st.session_state.chess_username)
        if not ok:
            st.error(err)
        st.rerun()
    
    if st.sidebar.button("Switch User"):
        st.session_state.switching_user = True
        st.rerun()
    
    overview = st.Page("pages/1_Overview.py", title="Overview", default=True)
    tilt = st.Page("pages/2_Tilt_Tracker.py", title="Tilt Tracker")
    when = st.Page("pages/3_When_To_Play.py", title="When To Play")
    opening = st.Page("pages/4_Opening_Lab.py", title="Opening Lab")
    opponent = st.Page("pages/5_Know_Your_Opponent.py", title="Know Your Opponent")
    session = st.Page("pages/6_Session_Insights.py", title="Session Insights")
    replay = st.Page("pages/7_Game_Replay.py", title="Game Replay")

    pg = st.navigation([overview, tilt, when, opening, opponent, session, replay])
    pg.run()