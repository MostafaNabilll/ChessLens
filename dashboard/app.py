import streamlit as st
import requests
import subprocess
import sys
from pathlib import Path

st.set_page_config(page_title="ChessLens", page_icon="♟️", layout="wide")

DB_PATH = str(Path(__file__).parent.parent / "data" / "chesslens.duckdb")

if 'chess_username' not in st.session_state:
    st.title("ChessLens")
    st.write("Enter your chess.com username to get started.")
    
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
                
                import duckdb
                import os
                
                os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
                
                try:
                    conn = duckdb.connect(DB_PATH, read_only=True)
                    cnt = conn.execute(f"""
                        SELECT COUNT(*) as cnt 
                        FROM raw_games 
                        WHERE username = '{username.lower()}'
                    """).fetchone()[0]
                    conn.close()
                except:
                    cnt = 0
                
                if cnt == 0:
                    with st.spinner(f"Pulling games for {username}... This may take a minute."):
                        result = subprocess.run([
                            sys.executable, 
                            str(Path(__file__).parent.parent / "ingestion" / "extract.py"),
                            "--backfill",
                            "--username", username.lower()
                        ], capture_output=True, text=True)
                    
                    if result.returncode != 0:
                        st.error(f"Ingestion failed: {result.stderr}")
                        del st.session_state.chess_username
                        st.stop()
                    
                    with st.spinner("Transforming data..."):
                        dbt_path = str(Path(sys.executable).parent / "dbt.exe")
                        dbt_project = str(Path(__file__).parent.parent / "dbt_chesslens")
                        result = subprocess.run([
                            dbt_path, "build", "--full-refresh",
                            "--project-dir", dbt_project,
                            "--profiles-dir", dbt_project
                        ], capture_output=True, text=True, cwd=dbt_project)
                    
                    if result.returncode != 0:
                        st.error(f"dbt failed: {result.stderr}")
                        st.error(f"dbt stdout: {result.stdout}")
                        del st.session_state.chess_username
                        st.stop()
                
                st.rerun()

else:
    st.sidebar.title("ChessLens")
    st.sidebar.caption(f"Player: {st.session_state.chess_username}")
    
    if st.sidebar.button("Refresh Data"):
        with st.spinner("Updating games..."):
            result = subprocess.run([
                sys.executable,
                str(Path(__file__).parent.parent / "ingestion" / "extract.py"),
                "--username", st.session_state.chess_username
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                dbt_path = str(Path(sys.executable).parent / "dbt.exe")
                dbt_project = str(Path(__file__).parent.parent / "dbt_chesslens")
                subprocess.run([
                    dbt_path, "build", "--full-refresh",
                    "--project-dir", dbt_project,
                    "--profiles-dir", dbt_project
                ], capture_output=True, text=True, cwd=dbt_project)
        st.rerun()
    
    if st.sidebar.button("Switch User"):
        del st.session_state.chess_username
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