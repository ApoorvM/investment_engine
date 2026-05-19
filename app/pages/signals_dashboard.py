"""
Signals dashboard page for the Investment Engine.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from app.services.signals import SignalsService
from app.services.market_data import MarketDataService
from app.components.tables import render_signals_table, render_screening_table
from app.components.filters import render_signal_filter, render_sector_filter
from app.components.charts import render_signal_distribution_chart
from app.state.session import SessionState
from app.utils.formatting import format_percentage, format_currency

def render_signals_dashboard():
    """Render the signals dashboard page."""
    st.markdown('<div class="main-header">🚨 Signals Dashboard</div>', unsafe_allow_html=True)
    st.markdown("Monitor and analyze trading signals across the portfolio.")

    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        selected_signal = render_signal_filter()
    with col2:
        selected_sector = render_sector_filter()
    with col3:
        min_confidence = st.slider("Min Confidence", 0, 100, 50, key="signal_confidence")

    selected_index = SessionState.get('selected_index', 'NIFTY50')
    index_name = selected_index.lower()

    # Load signals data
    try:
        signals_df = SignalsService.get_latest_signals(index_name=index_name)
        screen_df = SignalsService.get_screen_results(index_name=index_name)
        universe_df = MarketDataService.get_universe_data(index_name=index_name)

        if not signals_df.empty:
            # Apply filters
            filtered_signals = signals_df.copy()
            if selected_signal != "All":
                filtered_signals = filtered_signals[filtered_signals['Signal'] == selected_signal]
            if selected_sector != "All" and 'Sector' in filtered_signals.columns:
                filtered_signals = filtered_signals[filtered_signals['Sector'] == selected_sector]
            if 'Confidence' in filtered_signals.columns:
                filtered_signals = filtered_signals[filtered_signals['Confidence'] >= min_confidence]

            # Signal summary
            st.subheader("📊 Signal Summary")
            summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)

            with summary_col1:
                st.metric("Total Signals", len(filtered_signals))
            with summary_col2:
                buy_signals = len(filtered_signals[filtered_signals['Signal'] == 'BUY'])
                st.metric("Buy Signals", buy_signals)
            with summary_col3:
                sell_signals = len(filtered_signals[filtered_signals['Signal'] == 'SELL'])
                st.metric("Sell Signals", sell_signals)
            with summary_col4:
                hold_signals = len(filtered_signals[filtered_signals['Signal'] == 'HOLD'])
                st.metric("Hold Signals", hold_signals)

            # Signal distribution chart
            st.subheader("📈 Signal Distribution")
            render_signal_distribution_chart(filtered_signals)

            # Signals table
            st.subheader("📋 Current Signals")
            render_signals_table(filtered_signals)

            # Screening results
            if not screen_df.empty:
                st.subheader("🔍 Screening Results")
                # Apply same filters
                filtered_screen = screen_df.copy()
                if selected_sector != "All" and 'Sector' in filtered_screen.columns:
                    filtered_screen = filtered_screen[filtered_screen['Sector'] == selected_sector]

                render_screening_table(filtered_screen)

        else:
            st.warning("No signals data available. Please run the signal generation pipeline.")

        # Signal performance
        st.subheader("📊 Signal Performance")
        if not signals_df.empty and 'Signal' in signals_df.columns:
            # Calculate signal success rates (placeholder logic)
            signal_performance = signals_df.groupby('Signal').size().reset_index(name='Count')
            signal_performance['Percentage'] = (signal_performance['Count'] / signal_performance['Count'].sum()) * 100

            fig = px.pie(signal_performance, values='Count', names='Signal',
                        title='Signal Distribution by Type',
                        color_discrete_map={'BUY': 'green', 'SELL': 'red', 'HOLD': 'orange'})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Signal performance data will be available after backtesting.")

    except Exception as e:
        st.error(f"Error loading signals data: {e}")
        st.info("Make sure the signals pipeline has been run.")
