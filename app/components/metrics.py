"""
Metrics display components for the dashboard.
"""

import streamlit as st
import pandas as pd
from app.services.market_data import MarketDataService
from app.utils.formatting import format_currency, format_percentage, format_number

def render_metric_card(title: str, value: str, delta: str = None, card_type: str = "default"):
    """Display a metric card with title, value, and optional delta."""
    # Color coding based on card type
    colors = {
        "default": "#1f77b4",
        "signals": "#ff7f0e",
        "portfolio": "#2ca02c",
        "health": "#d62728"
    }
    color = colors.get(card_type, colors["default"])

    st.markdown(f"""
    <div style="background-color: #f0f2f6; padding: 1rem; border-radius: 0.5rem; border-left: 4px solid {color}; margin-bottom: 1rem;">
        <div style="font-size: 0.8rem; color: #666; margin-bottom: 0.5rem;">{title}</div>
        <div style="font-size: 1.5rem; font-weight: bold; color: #000;">{value}</div>
        {"<div style='font-size: 0.8rem; color: #666;'>" + delta + "</div>" if delta else ""}
    </div>
    """, unsafe_allow_html=True)

def render_stock_metrics(symbol: str, ohlcv_df: pd.DataFrame, indicators_df: pd.DataFrame):
    """Render key metrics for a stock."""
    if ohlcv_df.empty:
        st.warning("No OHLCV data available for metrics.")
        return

    # Calculate basic metrics
    latest_price = ohlcv_df['Close'].iloc[-1] if not ohlcv_df.empty else 0
    prev_price = ohlcv_df['Close'].iloc[-2] if len(ohlcv_df) > 1 else latest_price
    price_change = latest_price - prev_price
    price_change_pct = (price_change / prev_price) * 100 if prev_price != 0 else 0

    # Volume
    latest_volume = ohlcv_df['Volume'].iloc[-1] if 'Volume' in ohlcv_df.columns else 0
    avg_volume = ohlcv_df['Volume'].mean() if 'Volume' in ohlcv_df.columns else 0

    # Technical indicators
    rsi = indicators_df['RSI'].iloc[-1] if not indicators_df.empty and 'RSI' in indicators_df.columns else None
    macd = indicators_df['MACD'].iloc[-1] if not indicators_df.empty and 'MACD' in indicators_df.columns else None

    # Display metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        render_metric_card(
            "Current Price",
            format_currency(latest_price),
            f"{format_percentage(price_change_pct)}",
            "default"
        )

    with col2:
        render_metric_card(
            "Volume",
            format_number(latest_volume),
            f"vs {format_number(avg_volume)} avg",
            "default"
        )

    with col3:
        if rsi is not None:
            rsi_signal = "Overbought" if rsi > 70 else "Oversold" if rsi < 30 else "Neutral"
            render_metric_card(
                "RSI",
                format_number(rsi, 1),
                rsi_signal,
                "signals"
            )
        else:
            render_metric_card("RSI", "N/A", "", "default")

    with col4:
        if macd is not None:
            macd_signal = "Bullish" if macd > 0 else "Bearish"
            render_metric_card(
                "MACD",
                format_number(macd, 2),
                macd_signal,
                "signals"
            )
        else:
            render_metric_card("MACD", "N/A", "", "default")

def render_performance_metrics(performance_summary: dict):
    """Render performance metrics cards."""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        render_metric_card(
            "Total Return",
            format_percentage(performance_summary.get('total_return', 0)),
            "",
            "portfolio"
        )

    with col2:
        render_metric_card(
            "CAGR",
            format_percentage(performance_summary.get('cagr', 0)),
            "",
            "portfolio"
        )

    with col3:
        render_metric_card(
            "Sharpe Ratio",
            format_number(performance_summary.get('sharpe', 0), 2),
            "",
            "portfolio"
        )

    with col4:
        render_metric_card(
            "Max Drawdown",
            format_percentage(performance_summary.get('max_drawdown', 0)),
            "",
            "health"
        )

def display_metric_card(title: str, value: str, delta: str = None, help_text: str = None):
    """Display a metric card with title, value, and optional delta."""
    if delta:
        st.metric(title, value, delta, help=help_text)
    else:
        st.metric(title, value, help=help_text)

def display_kpi_grid(kpis: dict):
    """Display a grid of KPI metrics."""
    cols = st.columns(len(kpis))
    for i, (title, data) in enumerate(kpis.items()):
        with cols[i]:
            display_metric_card(
                title=title,
                value=data.get('value', 'N/A'),
                delta=data.get('delta'),
                help_text=data.get('help')
            )