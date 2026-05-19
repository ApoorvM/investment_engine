"""
Chart components for the Investment Engine dashboard.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from typing import List, Optional


def _find_column(df: pd.DataFrame, candidates: list) -> Optional[str]:
    for col in candidates:
        if col in df.columns:
            return col
    return None


def _get_datetime_index(df: pd.DataFrame):
    if isinstance(df.index, pd.DatetimeIndex):
        return df.index

    date_col = _find_column(df, ['Date', 'date', 'timestamp', 'time'])
    if date_col is not None:
        return pd.to_datetime(df[date_col], errors='coerce')

    return df.index


def render_price_chart(df: pd.DataFrame, symbol: str, chart_type: str = "Candlestick"):
    """Render price chart for a symbol."""
    if df.empty:
        st.warning("No data available for chart.")
        return

    open_col = _find_column(df, ['Open', 'open'])
    high_col = _find_column(df, ['High', 'high'])
    low_col = _find_column(df, ['Low', 'low'])
    close_col = _find_column(df, ['Close', 'close'])
    x_axis = _get_datetime_index(df)

    if not all([open_col, high_col, low_col, close_col]):
        st.warning("OHLCV data incomplete for price chart.")
        return

    fig = go.Figure()

    if chart_type == "Candlestick":
        fig.add_trace(go.Candlestick(
            x=x_axis,
            open=df[open_col],
            high=df[high_col],
            low=df[low_col],
            close=df[close_col],
            name=symbol
        ))
    elif chart_type == "Line":
        fig.add_trace(go.Scatter(
            x=x_axis,
            y=df[close_col],
            mode='lines',
            name=f'{symbol} Close'
        ))
    elif chart_type == "OHLC":
        fig.add_trace(go.Ohlc(
            x=x_axis,
            open=df[open_col],
            high=df[high_col],
            low=df[low_col],
            close=df[close_col],
            name=symbol
        ))

    fig.update_layout(
        title=f'{symbol} Price Chart',
        yaxis_title='Price (₹)',
        xaxis_title='Date',
        height=500
    )

    st.plotly_chart(fig, use_container_width=True)


def render_indicator_chart(df: pd.DataFrame, indicators_df: pd.DataFrame,
                          indicator_cols: List[str], title: str,
                          y_range: Optional[List[float]] = None):
    """Render technical indicator chart."""
    if indicators_df.empty:
        st.warning("No indicator data available.")
        return

    fig = go.Figure()
    close_col = _find_column(df, ['Close', 'close'])
    x_axis = _get_datetime_index(df)

    if close_col is not None:
        fig.add_trace(go.Scatter(
            x=x_axis,
            y=df[close_col],
            mode='lines',
            name='Close Price',
            line=dict(color='lightgray', width=1),
            yaxis="y2"
        ))

    colors = ['blue', 'red', 'green', 'orange', 'purple']
    for i, col in enumerate(indicator_cols):
        if col in indicators_df.columns:
            color = colors[i % len(colors)]
            fig.add_trace(go.Scatter(
                x=_get_datetime_index(indicators_df),
                y=indicators_df[col],
                mode='lines',
                name=col,
                line=dict(color=color, width=2)
            ))

    layout_kwargs = {
        'title': title,
        'xaxis_title': 'Date',
        'height': 400
    }

    if y_range:
        layout_kwargs['yaxis_range'] = y_range

    if close_col is not None:
        layout_kwargs.update({
            'yaxis2': dict(
                title='Price (₹)',
                overlaying='y',
                side='right',
                showgrid=False
            ),
            'yaxis_title': 'Indicator Value'
        })

    fig.update_layout(**layout_kwargs)
    st.plotly_chart(fig, use_container_width=True)


def render_volume_chart(df: pd.DataFrame, symbol: str):
    """Render volume chart."""
    volume_col = _find_column(df, ['Volume', 'volume'])
    close_col = _find_column(df, ['Close', 'close'])

    if volume_col is None:
        st.warning("No volume data available.")
        return

    fig = go.Figure()
    colors = []
    if close_col is not None and _find_column(df, ['Open', 'open']):
        open_col = _find_column(df, ['Open', 'open'])
        close_col = _find_column(df, ['Close', 'close'])
        colors = ['red' if row[close_col] < row[open_col] else 'green' for _, row in df.iterrows()]
    else:
        colors = ['blue'] * len(df)

    fig.add_trace(go.Bar(
        x=_get_datetime_index(df),
        y=df[volume_col],
        name='Volume',
        marker_color=colors,
        opacity=0.7
    ))

    fig.update_layout(
        title=f'{symbol} Volume Chart',
        yaxis_title='Volume',
        xaxis_title='Date',
        height=300
    )

    st.plotly_chart(fig, use_container_width=True)


def render_equity_curve_chart(equity_df: pd.DataFrame):
    """Render equity curve chart."""
    equity_col = _find_column(equity_df, ['Equity', 'equity'])
    if equity_df.empty or equity_col is None:
        st.warning("No equity curve data available.")
        return

    x_axis = _get_datetime_index(equity_df)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x_axis,
        y=equity_df[equity_col],
        mode='lines',
        name='Portfolio Value',
        line=dict(color='blue', width=2)
    ))

    fig.update_layout(
        title='Portfolio Equity Curve',
        yaxis_title='Portfolio Value (₹)',
        xaxis_title='Date',
        height=400
    )

    st.plotly_chart(fig, use_container_width=True)


def render_sector_heatmap(sector_data: pd.DataFrame):
    """Render sector allocation heatmap."""
    if sector_data.empty:
        st.warning("No sector data available.")
        return

    sector_col = _find_column(sector_data, ['Sector', 'sector'])
    value_col = _find_column(sector_data, ['Market_Cap', 'market_cap'])
    if sector_col is None or value_col is None:
        st.warning("Sector allocation data is unavailable.")
        return

    fig = px.treemap(
        sector_data,
        path=[sector_col],
        values=value_col,
        title='Sector Allocation by Market Cap',
        color=value_col,
        color_continuous_scale='Blues'
    )

    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)


def render_market_cap_chart(df: pd.DataFrame):
    """Render market cap distribution chart."""
    market_cap_col = _find_column(df, ['Market_Cap', 'market_cap'])
    if market_cap_col is None:
        st.warning("No market cap data available.")
        return

    df_copy = df.copy()
    df_copy[market_cap_col] = pd.to_numeric(df_copy[market_cap_col], errors='coerce')
    if df_copy[market_cap_col].dropna().empty:
        st.warning("No market cap data available.")
        return

    df_copy['Market_Cap_Category'] = pd.cut(
        df_copy[market_cap_col].fillna(0),
        bins=[-1, 5000, 20000, 50000, float('inf')],
        labels=['Small Cap', 'Mid Cap', 'Large Cap', 'Mega Cap']
    )

    cap_distribution = df_copy.groupby('Market_Cap_Category')[market_cap_col].sum().reset_index()

    fig = px.pie(
        cap_distribution,
        values=market_cap_col,
        names='Market_Cap_Category',
        title='Market Cap Distribution',
        color_discrete_sequence=px.colors.qualitative.Set3
    )

    st.plotly_chart(fig, use_container_width=True)


def render_sector_allocation_chart(sector_data: pd.DataFrame):
    """Render sector allocation pie chart."""
    if sector_data.empty:
        st.warning("No sector allocation data available.")
        return

    value_col = _find_column(sector_data, ['Allocated_Capital', 'allocated_capital'])
    sector_col = _find_column(sector_data, ['Sector', 'sector'])
    if value_col is None or sector_col is None:
        st.warning("Sector allocation data is unavailable.")
        return

    fig = px.pie(
        sector_data,
        values=value_col,
        names=sector_col,
        title='Portfolio Sector Allocation',
        color_discrete_sequence=px.colors.qualitative.Set3
    )

    st.plotly_chart(fig, use_container_width=True)


def render_portfolio_performance_chart(performance_df: pd.DataFrame):
    """Render portfolio performance chart."""
    if performance_df.empty:
        st.warning("No performance data available.")
        return

    returns_col = _find_column(performance_df, ['Returns', 'returns'])
    if returns_col is None:
        st.warning("No performance returns available.")
        return

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=_get_datetime_index(performance_df),
        y=performance_df[returns_col],
        mode='lines',
        name='Portfolio Returns',
        line=dict(color='green', width=2)
    ))

    fig.update_layout(
        title='Portfolio Performance',
        yaxis_title='Returns (%)',
        xaxis_title='Date',
        height=400
    )

    st.plotly_chart(fig, use_container_width=True)


def render_drawdown_chart(equity_df: pd.DataFrame):
    """Render drawdown chart."""
    drawdown_col = _find_column(equity_df, ['Drawdown', 'drawdown'])
    equity_col = _find_column(equity_df, ['Equity', 'equity'])

    if drawdown_col is None and equity_col is None:
        st.warning("No drawdown or equity data available.")
        return

    if drawdown_col is None:
        equity_df = equity_df.copy()
        equity_df['Drawdown'] = equity_df[equity_col] / equity_df[equity_col].cummax() - 1
        drawdown_col = 'Drawdown'

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=_get_datetime_index(equity_df),
        y=equity_df[drawdown_col] * 100,
        fill='tozeroy',
        mode='lines',
        name='Drawdown',
        line=dict(color='red', width=2)
    ))

    fig.update_layout(
        title='Portfolio Drawdown',
        yaxis_title='Drawdown (%)',
        xaxis_title='Date',
        height=400
    )

    st.plotly_chart(fig, use_container_width=True)


def render_returns_distribution(equity_df: pd.DataFrame):
    """Render returns distribution histogram."""
    returns_col = _find_column(equity_df, ['Returns', 'returns', 'period_return', 'return'])
    if returns_col is None:
        st.warning("No returns data available.")
        return

    fig = px.histogram(
        equity_df,
        x=returns_col,
        title='Returns Distribution',
        labels={returns_col: 'Daily Returns (%)'},
        nbins=50
    )

    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)


def render_signal_distribution_chart(signals_df: pd.DataFrame):
    """Render signal distribution chart."""
    signal_col = _find_column(signals_df, ['Signal', 'signal'])
    if signals_df.empty or signal_col is None:
        st.warning("No signal data available.")
        return

    signal_counts = signals_df[signal_col].value_counts().reset_index()
    signal_counts.columns = ['Signal', 'Count']

    fig = px.bar(
        signal_counts,
        x='Signal',
        y='Count',
        title='Signal Distribution',
        color='Signal',
        color_discrete_map={'BUY': 'green', 'SELL': 'red', 'HOLD': 'orange'}
    )

    st.plotly_chart(fig, use_container_width=True)
