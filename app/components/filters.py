"""
Filter components for data selection.
"""

import streamlit as st
from typing import List, Optional
from app.services.market_data import MarketDataService

def render_symbol_filter(index_name: str = "nifty50") -> Optional[str]:
    """Render symbol selection filter."""
    try:
        universe_df = MarketDataService.get_universe_data(index_name=index_name)
        if not universe_df.empty and 'Symbol' in universe_df.columns:
            symbols = sorted(universe_df['Symbol'].unique())
            return st.selectbox("Select Symbol", symbols, key="symbol_select")
    except Exception:
        pass
    return st.selectbox("Select Symbol", ["RELIANCE", "TCS", "INFY", "HDFC"], key="symbol_select")

def render_sector_filter(index_name: str = "nifty50") -> Optional[str]:
    """Render sector selection filter."""
    try:
        universe_df = MarketDataService.get_universe_data(index_name=index_name)
        if not universe_df.empty and 'Sector' in universe_df.columns:
            sectors = sorted(universe_df['Sector'].dropna().unique())
            return st.selectbox("Select Sector", ["All"] + sectors, key="sector_select")
    except Exception:
        pass
    return st.selectbox("Select Sector", ["All", "Technology", "Finance", "Energy"], key="sector_select")

def render_signal_filter() -> Optional[str]:
    """Render signal type filter."""
    return st.selectbox("Signal Type", ["All", "BUY", "SELL", "HOLD"], key="signal_select")

def render_market_cap_filter() -> Optional[str]:
    """Render market cap filter."""
    return st.selectbox("Market Cap", ["All", "Large Cap", "Mid Cap", "Small Cap"], key="market_cap_select")

def symbol_filter(symbols: List[str], key: str = "symbol_filter") -> Optional[str]:
    """Symbol selection filter."""
    return st.selectbox(
        "Select Symbol",
        ["All"] + symbols,
        key=key
    )

def sector_filter(sectors: List[str], key: str = "sector_filter") -> Optional[str]:
    """Sector selection filter."""
    return st.selectbox(
        "Select Sector",
        ["All"] + sectors,
        key=key
    )

def signal_filter(signals: List[str], key: str = "signal_filter") -> Optional[str]:
    """Signal type filter."""
    return st.selectbox(
        "Signal Type",
        ["All"] + signals,
        key=key
    )

def date_range_filter(key: str = "date_range"):
    """Date range filter."""
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", key=f"{key}_start")
    with col2:
        end_date = st.date_input("End Date", key=f"{key}_end")
    return start_date, end_date