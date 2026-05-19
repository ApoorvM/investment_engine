"""
Table display components.
"""

import streamlit as st
import pandas as pd
from app.utils.formatting import format_currency, format_percentage, format_number, format_signal

def render_signals_table(signals_df: pd.DataFrame):
    """Render signals table with formatting."""
    if signals_df.empty:
        st.info("No signals data available.")
        return

    # Format the dataframe for display
    display_df = signals_df.copy()

    # Format columns
    if 'Signal' in display_df.columns:
        display_df['Signal'] = display_df['Signal'].apply(format_signal)

    if 'Confidence' in display_df.columns:
        display_df['Confidence'] = display_df['Confidence'].apply(lambda x: format_percentage(x) if pd.notna(x) else 'N/A')

    if 'Price' in display_df.columns:
        display_df['Price'] = display_df['Price'].apply(lambda x: format_currency(x) if pd.notna(x) else 'N/A')

    if 'Stop_Loss' in display_df.columns:
        display_df['Stop_Loss'] = display_df['Stop_Loss'].apply(lambda x: format_currency(x) if pd.notna(x) else 'N/A')

    # Select columns to display
    display_cols = ['Symbol', 'Company_Name', 'Sector', 'Signal', 'Confidence', 'Price', 'Stop_Loss']
    available_cols = [col for col in display_cols if col in display_df.columns]

    st.dataframe(display_df[available_cols], use_container_width=True)

def render_screening_table(screen_df: pd.DataFrame):
    """Render screening results table."""
    if screen_df.empty:
        st.info("No screening data available.")
        return

    # Format the dataframe for display
    display_df = screen_df.copy()

    # Format numeric columns
    numeric_cols = ['Momentum_Score', 'Trend_Score', 'Volatility_Score', 'Composite_Score']
    for col in numeric_cols:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(lambda x: format_number(x, 2) if pd.notna(x) else 'N/A')

    # Select columns to display
    display_cols = ['Symbol', 'Company_Name', 'Sector', 'Momentum_Score', 'Trend_Score', 'Volatility_Score', 'Composite_Score', 'Selected']
    available_cols = [col for col in display_cols if col in display_df.columns]

    st.dataframe(display_df[available_cols], use_container_width=True)

def render_portfolio_table(positions_df: pd.DataFrame):
    """Render portfolio positions table."""
    if positions_df.empty:
        st.info("No portfolio positions available.")
        return

    # Format the dataframe for display
    display_df = positions_df.copy()

    # Format currency columns
    currency_cols = ['Allocated_Capital', 'Current_Value', 'Unrealized_PnL']
    for col in currency_cols:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(lambda x: format_currency(x) if pd.notna(x) else 'N/A')

    # Format percentage columns
    pct_cols = ['Weight', 'Return']
    for col in pct_cols:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(lambda x: format_percentage(x) if pd.notna(x) else 'N/A')

    # Select columns to display
    display_cols = ['Symbol', 'Company_Name', 'Sector', 'Allocated_Capital', 'Weight', 'Current_Value', 'Unrealized_PnL', 'Return']
    available_cols = [col for col in display_cols if col in display_df.columns]

    st.dataframe(display_df[available_cols], use_container_width=True)

def render_trades_table(trades_df: pd.DataFrame):
    """Render trades log table."""
    if trades_df.empty:
        st.info("No trades data available.")
        return

    # Format the dataframe for display
    display_df = trades_df.copy()

    # Format currency columns
    currency_cols = ['Entry_Price', 'Exit_Price', 'PnL']
    for col in currency_cols:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(lambda x: format_currency(x) if pd.notna(x) else 'N/A')

    # Format date columns
    date_cols = ['Entry_Date', 'Exit_Date']
    for col in date_cols:
        if col in display_df.columns:
            display_df[col] = pd.to_datetime(display_df[col]).dt.strftime('%Y-%m-%d')

    # Select columns to display
    display_cols = ['Symbol', 'Side', 'Entry_Date', 'Entry_Price', 'Exit_Date', 'Exit_Price', 'Quantity', 'PnL']
    available_cols = [col for col in display_cols if col in display_df.columns]

    st.dataframe(display_df[available_cols], use_container_width=True)

def render_market_table(df: pd.DataFrame, title: str = "Market Data"):
    """Render market data table."""
    if df.empty:
        st.info(f"No {title.lower()} available.")
        return

    # Format the dataframe for display
    display_df = df.copy()

    # Format currency columns
    currency_cols = ['Market_Cap', 'Price']
    for col in currency_cols:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(lambda x: format_currency(x) if pd.notna(x) else 'N/A')

    # Format percentage columns
    pct_cols = ['Returns_1M', 'PE_Ratio']
    for col in pct_cols:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(lambda x: format_percentage(x) if pd.notna(x) else 'N/A')

    st.subheader(title)
    st.dataframe(display_df, use_container_width=True)

def display_data_table(df: pd.DataFrame, title: str = None, height: int = 400):
    """Display a data table with optional title."""
    if title:
        st.subheader(title)
    st.dataframe(df, use_container_width=True, height=height)

def display_signal_table(signals_df: pd.DataFrame):
    """Display signals table with color coding."""
    def color_signals(val):
        if val == 'BUY':
            return 'background-color: #d4edda; color: #155724'
        elif val == 'SELL':
            return 'background-color: #f8d7da; color: #721c24'
        elif val == 'HOLD':
            return 'background-color: #fff3cd; color: #856404'
        return ''

    styled_df = signals_df.style.applymap(color_signals, subset=['Signal'])
    st.dataframe(styled_df, use_container_width=True)