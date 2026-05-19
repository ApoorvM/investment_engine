"""
Stock analysis page for the Investment Engine.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from app.services.market_data import MarketDataService
from app.services.signals import SignalsService
from app.components.charts import render_price_chart, render_indicator_chart, render_volume_chart
from app.components.filters import render_symbol_filter
from app.components.metrics import render_stock_metrics
from app.state.session import SessionState
from app.utils.formatting import format_currency, format_percentage, format_number

def render_stock_analysis():
    """Render the stock analysis page."""
    st.markdown('<div class="main-header">📈 Stock Analysis</div>', unsafe_allow_html=True)
    st.markdown("Detailed technical analysis for individual stocks.")

    selected_index = SessionState.get('selected_index', 'NIFTY50')
    index_name = selected_index.lower()

    # Symbol selection
    selected_symbol = render_symbol_filter(index_name=index_name)

    if selected_symbol:
        try:
            # Load stock data
            ohlcv_df = MarketDataService.get_ohlcv_data(selected_symbol, index_name=index_name)
            indicators_df = MarketDataService.get_indicators_data(selected_symbol, index_name=index_name)
            signals_df = SignalsService.get_latest_signals(index_name=index_name)

            if not ohlcv_df.empty:
                # Stock metrics
                st.subheader(f"📊 {selected_symbol} Metrics")
                render_stock_metrics(selected_symbol, ohlcv_df, indicators_df)

                # Price chart
                st.subheader("💹 Price Chart")
                chart_type = st.selectbox("Chart Type", ["Candlestick", "Line", "OHLC"], key="price_chart_type")
                timeframe = st.selectbox("Timeframe", ["All", "1M", "3M", "6M", "1Y", "2Y"], key="price_timeframe")

                # Filter data by timeframe
                if timeframe == "All":
                    chart_df = ohlcv_df
                elif timeframe.endswith("M"):
                    months = int(timeframe[:-1])
                    cutoff_date = pd.Timestamp.now() - pd.DateOffset(months=months)
                    chart_df = ohlcv_df[ohlcv_df.index >= cutoff_date]
                elif timeframe.endswith("Y"):
                    years = int(timeframe[:-1])
                    cutoff_date = pd.Timestamp.now() - pd.DateOffset(years=years)
                    chart_df = ohlcv_df[ohlcv_df.index >= cutoff_date]
                else:
                    chart_df = ohlcv_df

                render_price_chart(chart_df, selected_symbol, chart_type)

                # Technical indicators
                st.subheader("📈 Technical Indicators")
                indicator_tabs = st.tabs(["Moving Averages", "RSI", "MACD", "Volume"])

                with indicator_tabs[0]:
                    if not indicators_df.empty and 'SMA_20' in indicators_df.columns:
                        render_indicator_chart(chart_df, indicators_df, ['SMA_20', 'SMA_50', 'EMA_20'], "Moving Averages")
                    else:
                        st.info("Moving average data not available.")

                with indicator_tabs[1]:
                    if not indicators_df.empty and 'RSI' in indicators_df.columns:
                        render_indicator_chart(chart_df, indicators_df, ['RSI'], "RSI", y_range=[0, 100])
                    else:
                        st.info("RSI data not available.")

                with indicator_tabs[2]:
                    if not indicators_df.empty and 'MACD' in indicators_df.columns:
                        macd_cols = ['MACD', 'MACD_Signal', 'MACD_Histogram']
                        if all(col in indicators_df.columns for col in macd_cols):
                            render_indicator_chart(chart_df, indicators_df, macd_cols, "MACD")
                        else:
                            st.info("MACD data not available.")
                    else:
                        st.info("MACD data not available.")

                with indicator_tabs[3]:
                    render_volume_chart(chart_df, selected_symbol)

                # Signal information
                st.subheader("🚨 Signal Analysis")
                if not signals_df.empty:
                    stock_signal = signals_df[signals_df['Symbol'] == selected_symbol]
                    if not stock_signal.empty:
                        signal = stock_signal.iloc[0]['Signal']
                        confidence = stock_signal.iloc[0].get('Confidence', 'N/A')

                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Current Signal", signal)
                        with col2:
                            st.metric("Confidence", f"{confidence}%")
                        with col3:
                            entry_price = stock_signal.iloc[0].get('Entry_Price', 'N/A')
                            st.metric("Entry Price", format_currency(entry_price) if entry_price != 'N/A' else 'N/A')
                    else:
                        st.info(f"No signals available for {selected_symbol}")
                else:
                    st.info("No signal data available.")

            else:
                st.warning(f"No data available for {selected_symbol}")

        except Exception as e:
            st.error(f"Error loading data for {selected_symbol}: {e}")
    else:
        st.info("Please select a symbol to view analysis.")