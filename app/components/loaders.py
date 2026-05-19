"""
Data loading components with caching.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import pyarrow.parquet as pq

@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_parquet_data(file_path: str) -> pd.DataFrame:
    """Load parquet file with caching."""
    try:
        return pd.read_parquet(file_path)
    except Exception as e:
        st.error(f"Error loading {file_path}: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_csv_data(file_path: str) -> pd.DataFrame:
    """Load CSV file with caching."""
    try:
        return pd.read_csv(file_path)
    except Exception as e:
        st.error(f"Error loading {file_path}: {e}")
        return pd.DataFrame()

def get_data_path(*path_parts: str) -> Path:
    """Get absolute path to data directory."""
    return Path(__file__).parent.parent.parent / "data" / Path(*path_parts)