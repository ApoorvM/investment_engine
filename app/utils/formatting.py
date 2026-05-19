"""
Formatting utilities for the dashboard.
"""

import pandas as pd
from typing import Any

def format_currency(value: float) -> str:
    """Format value as currency."""
    if pd.isna(value):
        return "N/A"
    return f"₹{value:,.2f}"

def format_percentage(value: float) -> str:
    """Format value as percentage."""
    if pd.isna(value):
        return "N/A"
    if -1 <= value <= 1:
        value = value * 100
    return f"{value:.2f}%"

def format_number(value: float, decimals: int = 2) -> str:
    """Format number with specified decimals."""
    if pd.isna(value):
        return "N/A"
    return f"{value:,.{decimals}f}"

def format_date(date: Any) -> str:
    """Format date for display."""
    if pd.isna(date):
        return "N/A"
    if isinstance(date, str):
        return date
    return date.strftime("%Y-%m-%d")

def format_signal(signal: str) -> str:
    """Format signal for display."""
    if pd.isna(signal):
        return "N/A"
    return signal.title()

def get_signal_color(signal: str) -> str:
    """Get color for signal."""
    colors = {
        'BUY': 'green',
        'SELL': 'red',
        'HOLD': 'orange'
    }
    return colors.get(signal.upper(), 'gray')
