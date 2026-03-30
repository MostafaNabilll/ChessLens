import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
import chess
import chess.svg
import chess.pgn
import io
from utils import run_query, apply_styles, get_tc_default, get_username, evaluate_game, get_cached_eval, calculate_accuracy

apply_styles()

st.header("Game Replay")

username = get_username()

# Compact filters
c1, c2, c3 = st.columns([1, 1, 4])
with c1:
    time_classes = run_query(f"SELECT DISTINCT time_class FROM main_silver.silver_games WHERE username = '{username}'")['time_class'].tolist()
    selected_tc = st.selectbox("Time Control", time_classes, index=get_tc_default(time_classes), key="replay_tc")
with c2:
    result_filter = st.selectbox("Result", ["All", "win", "loss", "draw"], key="replay_result")

query = f"""
    SELECT game_id, end_at, player_color, player_rating, opponent_rating, 
           result, result_type, opening_family, pgn, opponent_result_type, time_control
    FROM main_silver.silver_games 
    WHERE time_class = '{selected_tc}'
    AND username = '{username}'
"""
if result_filter != "All":
    query += f" AND result = '{result_filter}'"
query += " ORDER BY end_at DESC LIMIT 100"

df = run_query(query)

if df.empty:
    st.info("No games found for the selected filters.")
else:
    df['label'] = df.apply(
        lambda x: f"{x['end_at'].strftime('%b %d %H:%M')} | {x['result'].upper()} ({x['result_type']}) | {x['opening_family'] or 'Unknown'} | {int(x['player_rating'])} vs {int(x['opponent_rating'])}", 
        axis=1
    )
    
    with c3:
        selected_label = st.selectbox("Game", df['label'].tolist(), key="game_select")
    
    selected_game = df[df['label'] == selected_label].iloc[0]
    
    # Info bar
    if selected_game['result'] == 'win':
        display_result_type = selected_game['opponent_result_type']
    else:
        display_result_type = selected_game['result_type']
    
    st.markdown(f"""
        <div style="
            background: rgba(128,128,128,0.1); 
            border-radius: 8px; 
            padding: 8px 15px; 
            display: flex; 
            justify-content: space-around;
            align-items: center;
            margin: 5px 0 10px 0;
            font-size: 13px;
        ">
            <span><strong>{selected_game['result'].upper()}</strong> by {display_result_type}</span>
            <span>|</span>
            <span>Playing <strong>{selected_game['player_color'].title()}</strong></span>
            <span>|</span>
            <span>You: <strong>{int(selected_game['player_rating'])}</strong> | Opponent: <strong>{int(selected_game['opponent_rating'])}</strong></span>
            <span>|</span>
            <span>{selected_game['opening_family'] or 'Unknown'}</span>
        </div>
    """, unsafe_allow_html=True)
    
    pgn_text = selected_game['pgn']
    if pgn_text:
        pgn_io = io.StringIO(pgn_text)
        game = chess.pgn.read_game(pgn_io)
        
        if game:
            board = game.board()
            positions = [board.copy()]
            moves = []
            move_texts = []
            
            # Get initial time from time_control
            tc_str = str(selected_game['time_control'])
            initial_seconds = int(tc_str.split("+")[0]) if "+" in tc_str else int(tc_str)
            
            # Parse moves with clock times
            for node in game.mainline():
                move = node.move
                move_san = board.san(move)
                moves.append(move)
                board.push(move)
                positions.append(board.copy())
                
                comment = node.comment
                clock_seconds = None
                if "%clk" in comment:
                    clock_str = comment.split("%clk ")[1].split("]")[0]
                    parts = clock_str.split(":")
                    clock_seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
                
                move_texts.append({
                    'san': move_san,
                    'clock_seconds': clock_seconds
                })
            
            # Calculate time spent per move
            white_prev_clock = initial_seconds
            black_prev_clock = initial_seconds
            for i, mt in enumerate(move_texts):
                if mt['clock_seconds'] is not None:
                    if i % 2 == 0:
                        spent = white_prev_clock - mt['clock_seconds']
                        if spent < 0:
                            spent = 0
                        mt['time_spent'] = f"{spent:.1f}s" if spent < 60 else f"{spent / 60:.1f}m"
                        white_prev_clock = mt['clock_seconds']
                    else:
                        spent = black_prev_clock - mt['clock_seconds']
                        if spent < 0:
                            spent = 0
                        mt['time_spent'] = f"{spent:.1f}s" if spent < 60 else f"{spent / 60:.1f}m"
                        black_prev_clock = mt['clock_seconds']
                else:
                    mt['time_spent'] = ""
            
            total_moves = len(positions) - 1
            
            if 'move_pos' not in st.session_state:
                st.session_state.move_pos = 0
            if st.session_state.move_pos > total_moves:
                st.session_state.move_pos = total_moves
            
            # Check if analysis exists
            game_id = selected_game['game_id']
            cached_eval = get_cached_eval(game_id)
            has_eval = not cached_eval.empty
            
            # Analyze button
            if not has_eval:
                if st.button("Analyze with Stockfish", use_container_width=True):
                    progress_bar = st.progress(0, text="Analyzing positions...")
                    
                    def update_progress(pct):
                        progress_bar.progress(pct, text=f"Analyzing... {int(pct * 100)}%")
                    
                    cached_eval = evaluate_game(pgn_text, game_id, progress_callback=update_progress)
                    has_eval = not cached_eval.empty
                    progress_bar.empty()
                    st.rerun()
            
            # Show accuracy summary if analysis exists
            if has_eval:
                player_color = selected_game['player_color']
                
                white_moves = cached_eval[cached_eval['move_number'] % 2 == 1]
                black_moves = cached_eval[cached_eval['move_number'] % 2 == 0]
                
                white_avg_ep = white_moves['centipawn_loss'].mean() / 1000
                black_avg_ep = black_moves['centipawn_loss'].mean() / 1000
                
                white_acc = calculate_accuracy(white_avg_ep)
                black_acc = calculate_accuracy(black_avg_ep)
                
                if player_color == 'white':
                    player_moves = white_moves
                    player_acc = white_acc
                    opponent_acc = black_acc
                else:
                    player_moves = black_moves
                    player_acc = black_acc
                    opponent_acc = white_acc
                
                blunders = len(player_moves[player_moves['classification'] == 'blunder'])
                mistakes = len(player_moves[player_moves['classification'] == 'mistake'])
                inaccuracies = len(player_moves[player_moves['classification'] == 'inaccuracy'])
                good_moves = len(player_moves[player_moves['classification'] == 'good'])
                excellent_moves = len(player_moves[player_moves['classification'] == 'excellent'])
                best_moves = len(player_moves[player_moves['classification'] == 'best'])
                
                if player_acc >= 90:
                    p_color = "#2ecc71"
                elif player_acc >= 70:
                    p_color = "#f39c12"
                else:
                    p_color = "#e74c3c"
                
                if opponent_acc >= 90:
                    o_color = "#2ecc71"
                elif opponent_acc >= 70:
                    o_color = "#f39c12"
                else:
                    o_color = "#e74c3c"
                
                st.markdown(f"""
                    <div style="
                        background: rgba(128,128,128,0.1); 
                        border-radius: 8px; 
                        padding: 8px 15px; 
                        display: flex; 
                        justify-content: space-around;
                        align-items: center;
                        margin: 0 0 10px 0;
                        font-size: 13px;
                    ">
                        <span>You: <strong style="color:{p_color}; font-size:16px;">{player_acc:.1f}%</strong></span>
                        <span>Opponent: <strong style="color:{o_color}; font-size:16px;">{opponent_acc:.1f}%</strong></span>
                        <span>|</span>
                        <span style="color:#2ecc71;">Best: {best_moves}</span>
                        <span style="color:#66bb6a;">Excellent: {excellent_moves}</span>
                        <span style="color:#8bc34a;">Good: {good_moves}</span>
                        <span style="color:#f39c12;">Inaccuracy: {inaccuracies}</span>
                        <span style="color:#ff9800;">Mistake: {mistakes}</span>
                        <span style="color:#e74c3c;">Blunder: {blunders}</span>
                    </div>
                """, unsafe_allow_html=True)
            
            # Board and moves side by side
            board_col, moves_col = st.columns([1, 1])
            
            with board_col:
                move_num = st.session_state.move_pos
                current_board = positions[move_num]
                flipped = selected_game['player_color'] == 'black'
                last_move = moves[move_num - 1] if move_num > 0 else None
                
                svg = chess.svg.board(
                    current_board, 
                    flipped=flipped,
                    lastmove=last_move,
                    size=570
                )
                
                # Eval bar next to board if analysis exists
                if has_eval and move_num > 0:
                    eval_row = cached_eval[cached_eval['move_number'] == move_num].iloc[0]
                    eval_score = eval_row['eval_after']
                    
                    # Clamp eval for display
                    clamped = max(-1000, min(1000, eval_score))
                    white_pct = 50 + (clamped / 20)
                    white_pct = max(5, min(95, white_pct))
                    black_pct = 100 - white_pct
                    
                    eval_display = f"+{eval_score / 100:.1f}" if eval_score >= 0 else f"{eval_score / 100:.1f}"
                    
                    eval_bar_html = f"""
                    <div style="display:flex; gap:10px; align-items:stretch; justify-content:center;">
                        <div style="width:25px; height:500px; border-radius:4px; overflow:hidden; display:flex; flex-direction:column; border:1px solid rgba(128,128,128,0.3);">
                            <div style="background:#333; height:{black_pct}%; transition:height 0.3s;"></div>
                            <div style="background:#eee; height:{white_pct}%; transition:height 0.3s;"></div>
                        </div>
                        <div>{svg}</div>
                    </div>
                    <div style="text-align:center; margin-top:5px; font-weight:bold; font-size:14px; color:gray;">{eval_display}</div>
                    """
                    st.markdown(eval_bar_html, unsafe_allow_html=True)
                else:
                    st.markdown(f'<div style="display:flex;justify-content:center;">{svg}</div>', unsafe_allow_html=True)
                
                # Spacing between board and buttons
                st.markdown("<div style='height: 20px'></div>", unsafe_allow_html=True)
                
                st.markdown("""
                    <style>
                        .replay-nav button {
                            border-radius: 8px;
                            font-weight: bold;
                            font-size: 18px;
                        }
                    </style>
                """, unsafe_allow_html=True)
                
                n1, n2, n3, n4, n5 = st.columns([1, 1, 2, 1, 1])
                with n1:
                    if st.button("<<", use_container_width=True):
                        st.session_state.move_pos = 0
                with n2:
                    if st.button("<", use_container_width=True):
                        if st.session_state.move_pos > 0:
                            st.session_state.move_pos -= 1
                with n3:
                    st.markdown(f"<div style='text-align:center; padding:10px; color:gray; font-size:14px; font-weight:bold;'>{move_num} / {total_moves}</div>", unsafe_allow_html=True)
                with n4:
                    if st.button("\\>", use_container_width=True):
                        if st.session_state.move_pos < total_moves:
                            st.session_state.move_pos += 1
                with n5:
                    if st.button("\\>>", use_container_width=True):
                        st.session_state.move_pos = total_moves
            
            with moves_col:
                # Classification colors for dots
                CLASS_COLORS = {
                    'best': '#2ecc71',
                    'excellent': '#66bb6a',
                    'good': '#8bc34a', 
                    'inaccuracy': '#f39c12',
                    'mistake': '#ff9800',
                    'blunder': '#e74c3c'
                }
                
                # Two-column move list with time spent and eval colors
                half = (len(move_texts) + 3) // 4 * 2
                
                move_html = '<div style="display:flex; gap:15px; max-height:500px; overflow-y:auto;">'
                
                for col_idx in range(2):
                    start = col_idx * half
                    end = min(start + half, len(move_texts))
                    
                    move_html += '<div style="flex:1; font-family:monospace; font-size:13px; line-height:1.9;">'
                    
                    i = start
                    while i < end:
                        move_number = i // 2 + 1
                        
                        if i < len(move_texts):
                            # White move
                            white_san = move_texts[i]['san']
                            white_time = move_texts[i]['time_spent']
                            
                            w_dot = ""
                            if has_eval and i < len(cached_eval):
                                w_class = cached_eval.iloc[i]['classification']
                                w_color = CLASS_COLORS.get(w_class, '')
                                if w_class in ('inaccuracy', 'mistake', 'blunder'):
                                    w_dot = f'<span style="color:{w_color}; font-size:8px;">&#9679;</span> '
                            
                            if i == move_num - 1:
                                w_style = "background:rgba(76,120,168,0.3); padding:1px 4px; border-radius:3px; font-weight:bold;"
                            else:
                                w_style = "padding:1px 4px;"
                            
                            time_tag = f'<span style="color:gray; font-size:10px;"> {white_time}</span>' if white_time else ''
                            
                            line = f'<span style="color:gray;">{move_number}.</span> '
                            line += f'{w_dot}<span style="{w_style}">{white_san}</span>{time_tag} '
                            
                            # Black move
                            if i + 1 < len(move_texts) and i + 1 < end:
                                black_san = move_texts[i + 1]['san']
                                black_time = move_texts[i + 1]['time_spent']
                                
                                b_dot = ""
                                if has_eval and i + 1 < len(cached_eval):
                                    b_class = cached_eval.iloc[i + 1]['classification']
                                    b_color = CLASS_COLORS.get(b_class, '')
                                    if b_class in ('inaccuracy', 'mistake', 'blunder'):
                                        b_dot = f'<span style="color:{b_color}; font-size:8px;">&#9679;</span> '
                                
                                if i + 1 == move_num - 1:
                                    b_style = "background:rgba(76,120,168,0.3); padding:1px 4px; border-radius:3px; font-weight:bold;"
                                else:
                                    b_style = "padding:1px 4px;"
                                
                                b_time_tag = f'<span style="color:gray; font-size:10px;"> {black_time}</span>' if black_time else ''
                                line += f'{b_dot}<span style="{b_style}">{black_san}</span>{b_time_tag}'
                            
                            move_html += line + '<br>'
                        
                        i += 2
                    
                    move_html += '</div>'
                
                move_html += '</div>'
                
                st.markdown(move_html, unsafe_allow_html=True)
                
                # Result at bottom
                result_text = game.headers.get("Result", "")
                if result_text:
                    st.markdown(f"<div style='text-align:center; margin-top:10px; font-weight:bold; color:gray; font-size:13px;'>{result_text}</div>", unsafe_allow_html=True)
        else:
            st.error("Could not parse the PGN for this game.")
    else:
        st.error("No PGN data available for this game.")