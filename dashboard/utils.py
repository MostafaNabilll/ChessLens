import duckdb
import pandas as pd
import streamlit as st
import chess
import chess.pgn
import subprocess
import shutil
import io
import os
import math
import time
from pathlib import Path

DB_PATH = str(Path(__file__).parent.parent / "data" / "chesslens.duckdb")


def _find_stockfish():
    path = shutil.which("stockfish")
    if path:
        return path
    if os.path.exists("/usr/games/stockfish"):
        return "/usr/games/stockfish"
    return str(Path(__file__).parent.parent / "bin" / "stockfish")


STOCKFISH_PATH = _find_stockfish()


def run_query(query: str, params=None, retries: int = 60) -> pd.DataFrame:
    for attempt in range(retries):
        try:
            with duckdb.connect(DB_PATH, read_only=True) as conn:
                if params:
                    return conn.execute(query, params).fetchdf()
                return conn.execute(query).fetchdf()
        except duckdb.IOException:
            if attempt == retries - 1:
                raise
            time.sleep(1)


def run_write(query: str, params=None):
    with duckdb.connect(DB_PATH) as conn:
        if params:
            conn.execute(query, params)
        else:
            conn.execute(query)


def apply_styles():
    st.markdown("""
        <style>
            .block-container { padding-top: 2rem; padding-bottom: 2rem; }
            [data-testid="stSidebar"] { min-width: 220px; max-width: 230px; }
            [data-testid="stMetricValue"], 
                [data-testid="stMetricDelta"] {white-space: nowrap;}
            [data-testid="stMetric"] { 
                background-color: rgba(128, 128, 128, 0.1); 
                padding: 15px; 
                border-radius: 10px;
                min-height: 120px;
                display: flex;
                flex-direction: column;
                justify-content: center;
            }
        </style>
    """, unsafe_allow_html=True)


def style_chart(fig, height=400, y_tickformat=None, showlegend=True):
    layout = dict(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        height=height,
        yaxis=dict(gridcolor='rgba(128,128,128,0.2)'),
        margin=dict(t=30, b=50),
        font=dict(size=13),
        showlegend=showlegend,
        coloraxis_showscale=False,
    )
    if y_tickformat:
        layout['yaxis_tickformat'] = y_tickformat
    fig.update_layout(**layout)
    return fig


def get_tc_default(options):
    if "All" in options:
        return options.index("All")
    if "rapid" in options:
        return options.index("rapid")
    return 0


def get_username():
    return st.session_state.get('chess_username', '')


def init_eval_table():
    run_write("""
        CREATE TABLE IF NOT EXISTS game_evaluations (
            game_id TEXT,
            move_number INT,
            eval_before INT,
            eval_after INT,
            centipawn_loss INT,
            classification TEXT,
            best_move TEXT,
            PRIMARY KEY (game_id, move_number)
        )
    """)


def get_cached_eval(game_id: str) -> pd.DataFrame:
    try:
        return run_query("""
            SELECT * FROM game_evaluations 
            WHERE game_id = ? 
            ORDER BY move_number
        """, [game_id])
    except duckdb.Error:
        return pd.DataFrame()


def cp_to_win_prob(cp):
    return 1 / (1 + 10 ** (-cp / 400))


def classify_move(ep_lost):
    if ep_lost <= 0.0:
        return "best"
    elif ep_lost <= 0.02:
        return "excellent"
    elif ep_lost <= 0.05:
        return "good"
    elif ep_lost <= 0.10:
        return "inaccuracy"
    elif ep_lost <= 0.20:
        return "mistake"
    else:
        return "blunder"


def calculate_accuracy(avg_ep_lost: float) -> float:
    if avg_ep_lost <= 0:
        return 100.0
    accuracy = 100 / (1 + math.exp(10 * (avg_ep_lost - 0.12)))
    return max(0, min(100, accuracy))


def get_eval(fen):
    proc = subprocess.Popen(
        [STOCKFISH_PATH],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    proc.stdin.write("uci\n")
    proc.stdin.write("isready\n")
    proc.stdin.write(f"position fen {fen}\n")
    proc.stdin.write("go depth 20\n")
    proc.stdin.flush()

    score = None
    while True:
        line = proc.stdout.readline()
        if not line:
            break
        if "score cp" in line:
            try:
                score = int(line.split("score cp ")[1].split(" ")[0])
            except (IndexError, ValueError):
                pass
        elif "score mate" in line:
            try:
                mate = int(line.split("score mate ")[1].split(" ")[0])
                score = 10000 if mate > 0 else -10000
            except (IndexError, ValueError):
                pass
        if "bestmove" in line:
            break

    proc.stdin.write("quit\n")
    proc.stdin.flush()
    proc.kill()

    # Stockfish scores from side to move, convert to white's perspective
    if fen.split(" ")[1] == "b" and score is not None:
        score = -score

    return score


def evaluate_game(pgn_text: str, game_id: str, progress_callback=None):
    init_eval_table()

    cached = get_cached_eval(game_id)
    if not cached.empty:
        return cached

    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if not game:
        return pd.DataFrame()

    board = game.board()
    moves_list = list(game.mainline_moves())
    evaluations = []

    prev_eval = get_eval(board.fen())

    for i, move in enumerate(moves_list):
        eval_before = prev_eval
        board.push(move)
        eval_after = get_eval(board.fen())

        if eval_before is not None and eval_after is not None:
            if i % 2 == 0:
                wp_before = cp_to_win_prob(eval_before)
                wp_after = cp_to_win_prob(eval_after)
            else:
                wp_before = cp_to_win_prob(-eval_before)
                wp_after = cp_to_win_prob(-eval_after)
            ep_lost = max(0, wp_before - wp_after)
            cp_loss_stored = int(ep_lost * 1000)
        else:
            ep_lost = 0
            cp_loss_stored = 0

        evaluations.append({
            'game_id': game_id,
            'move_number': i + 1,
            'eval_before': eval_before or 0,
            'eval_after': eval_after or 0,
            'centipawn_loss': cp_loss_stored,
            'classification': classify_move(ep_lost),
            'best_move': ''
        })

        prev_eval = eval_after

        if progress_callback:
            progress_callback((i + 1) / len(moves_list))

    with duckdb.connect(DB_PATH) as conn:
        for ev in evaluations:
            conn.execute("""
                INSERT INTO game_evaluations 
                (game_id, move_number, eval_before, eval_after, centipawn_loss, classification, best_move)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (game_id, move_number) DO NOTHING
            """, (ev['game_id'], ev['move_number'], ev['eval_before'], ev['eval_after'],
                  ev['centipawn_loss'], ev['classification'], ev['best_move']))

    return pd.DataFrame(evaluations)