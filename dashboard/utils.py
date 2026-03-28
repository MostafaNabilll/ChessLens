import duckdb
import pandas as pd
import streamlit as st
from pathlib import Path

DB_PATH = str(Path(__file__).parent.parent / "data" / "chesslens.duckdb")
conn = duckdb.connect(DB_PATH, read_only=True)

def run_query(query: str) -> pd.DataFrame:
    return conn.execute(query).fetchdf()

def get_tc_default(options):
    if "All" in options:
        return options.index("All")
    if "rapid" in options:
        return options.index("rapid")
    return 0
    
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