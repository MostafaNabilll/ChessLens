import duckdb
import pandas as pd
import streamlit as st
from pathlib import Path

DB_PATH = str(Path(__file__).parent.parent / "data" / "chesslens.duckdb")

def run_query(query: str) -> pd.DataFrame:
    conn = duckdb.connect(DB_PATH, read_only=True)
    result = conn.execute(query).fetchdf()
    conn.close()
    return result

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

def get_tc_default(options):
    if "All" in options:
        return options.index("All")
    if "rapid" in options:
        return options.index("rapid")
    return 0

def get_username():
    return st.session_state.get('chess_username', '')