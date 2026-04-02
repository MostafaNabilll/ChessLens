import duckdb
import pandas as pd
import streamlit as st
import chess
import chess.pgn
import subprocess
import io
import math
from pathlib import Path
import shutil

DB_PATH = str(Path(__file__).parent.parent / "data" / "chesslens.duckdb")
STOCKFISH_PATH = shutil.which("stockfish") or str(Path(__file__).parent.parent / "bin" / "stockfish")

def run_query(query: str, params=None) -> pd.DataFrame:
    conn = duckdb.connect(DB_PATH, read_only=True)
    if params:
        result = conn.execute(query, params).fetchdf()
    else:
        result = conn.execute(query).fetchdf()
    conn.close()
    return result

def run_write(query: str, params=None):
    conn = duckdb.connect(DB_PATH)
    if params:
        conn.execute(query, params)
    else:
        conn.execute(query)
    conn.close()

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
    conn = duckdb.connect(DB_PATH)
    conn.execute("""
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
    conn.close()

def get_cached_eval(game_id: str) -> pd.DataFrame:
    try:
        return run_query("""
            SELECT * FROM game_evaluations 
            WHERE game_id = ? 
            ORDER BY move_number
        """, [game_id])
    except:
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
    # Sigmoid curve that keeps most scores between 30-95
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
                cp_part = line.split("score cp ")[1].split(" ")[0]
                score = int(cp_part)
            except:
                pass
        elif "score mate" in line:
            try:
                mate_part = line.split("score mate ")[1].split(" ")[0]
                score = 10000 if int(mate_part) > 0 else -10000
            except:
                pass
        if "bestmove" in line:
            break
    
    proc.stdin.write("quit\n")
    proc.stdin.flush()
    proc.kill()
    
    # Stockfish returns score from side to move's perspective
    # Convert to white's perspective
    if fen.split(" ")[1] == "b":
        score = -score if score is not None else None
    
    return score

def evaluate_game(pgn_text: str, game_id: str, progress_callback=None):
    init_eval_table()
    
    cached = get_cached_eval(game_id)
    if not cached.empty:
        return cached
    
    pgn_io = io.StringIO(pgn_text)
    game = chess.pgn.read_game(pgn_io)
    if not game:
        return pd.DataFrame()
    
    board = game.board()
    moves_list = list(game.mainline_moves())
    evaluations = []
    
    # Initial position eval
    prev_eval = get_eval(board.fen())
    
    for i, move in enumerate(moves_list):
        eval_before = prev_eval
        
        board.push(move)
        eval_after = get_eval(board.fen())
        
        if eval_before is not None and eval_after is not None:
            if i % 2 == 0:  # white moved
                wp_before = cp_to_win_prob(eval_before)
                wp_after = cp_to_win_prob(eval_after)
            else:  # black moved
                wp_before = cp_to_win_prob(-eval_before)
                wp_after = cp_to_win_prob(-eval_after)
            
            ep_lost = max(0, wp_before - wp_after)
            # Store as integer (multiply by 1000 for precision in DB)
            cp_loss_stored = int(ep_lost * 1000)
        else:
            ep_lost = 0
            cp_loss_stored = 0
        
        classification = classify_move(ep_lost)
        
        evaluations.append({
            'game_id': game_id,
            'move_number': i + 1,
            'eval_before': eval_before or 0,
            'eval_after': eval_after or 0,
            'centipawn_loss': cp_loss_stored,
            'classification': classification,
            'best_move': ''
        }) 

        prev_eval = eval_after
        
        if progress_callback:
            progress_callback((i + 1) / len(moves_list))
    
    # Cache results
    conn = duckdb.connect(DB_PATH)
    for ev in evaluations:
        conn.execute("""
            INSERT INTO game_evaluations (game_id, move_number, eval_before, eval_after, centipawn_loss, classification, best_move)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (game_id, move_number) DO NOTHING
        """, (ev['game_id'], ev['move_number'], ev['eval_before'], ev['eval_after'], ev['centipawn_loss'], ev['classification'], ev['best_move']))
    conn.close()
    
    return pd.DataFrame(evaluations)